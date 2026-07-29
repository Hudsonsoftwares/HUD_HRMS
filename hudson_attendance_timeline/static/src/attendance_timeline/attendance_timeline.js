/** @odoo-module **/

import { Component, useSubEnv, useState, onWillStart, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

function getDateTime() {
    return (window.luxon && window.luxon.DateTime) || (typeof luxon !== "undefined" && luxon.DateTime);
}

// 1. MODEL CLASS
export class AttendanceTimelineModel {
    constructor(params, services) {
        this.setup(params, services);
    }

    setup(params, services) {
        this.orm = services.orm;
        this.notification = services.notification;

        const DateTime = getDateTime();
        this.currentDate = DateTime ? DateTime.now().startOf("day") : null;
        this.viewMode = "day";
        this.isLoading = false;

        this.employees = [];
        this.attendances = [];
        this.anomaliesMap = new Set();
        this.domain = (params && params.domain) || [];
    }

    async load(domain = this.domain) {
        const DateTime = getDateTime();
        if (!DateTime || !this.currentDate) return;

        this.domain = domain;
        this.isLoading = true;

        try {
            const dayStart = this.currentDate.startOf("day");
            const dayEnd = this.currentDate.endOf("day");

            const dayStartUTC = dayStart.toUTC().toFormat("yyyy-MM-dd HH:mm:ss");
            const dayEndUTC = dayEnd.toUTC().toFormat("yyyy-MM-dd HH:mm:ss");

            const empFields = ["id", "name", "display_name", "resource_calendar_id"];
            const empDomain = [...this._extractEmployeeDomain(domain)];
            const employeesData = await this.orm.searchRead("hr.employee", empDomain, empFields, { order: "name asc" });

            const attDomain = [
                ["check_in", "<=", dayEndUTC],
                "|",
                ["check_out", ">=", dayStartUTC],
                ["check_out", "=", false],
            ];

            const attFields = ["id", "employee_id", "check_in", "check_out", "worked_hours"];

            try {
                const attendanceModelFields = await this.orm.call("hr.attendance", "fields_get", [], {});
                if (attendanceModelFields.is_anomaly) {
                    attFields.push("is_anomaly");
                }
            } catch (e) {}

            const attData = await this.orm.searchRead("hr.attendance", attDomain, attFields);

            this.anomaliesMap = new Set();
            try {
                const anomalyRecords = await this.orm.searchRead(
                    "hudson.attendance.anomaly",
                    [["attendance_id", "!=", false]],
                    ["attendance_id"]
                );
                for (const a of anomalyRecords) {
                    if (a.attendance_id && a.attendance_id[0]) {
                        this.anomaliesMap.add(a.attendance_id[0]);
                    }
                }
            } catch (e) {}

            const now = DateTime.now();

            const processedAttendances = attData.map((att) => {
                const checkInLocal = DateTime.fromSQL(att.check_in, { zone: "utc" }).toLocal();
                let checkOutLocal = att.check_out
                    ? DateTime.fromSQL(att.check_out, { zone: "utc" }).toLocal()
                    : null;

                const isOngoing = !att.check_out;
                const effectiveEnd = isOngoing
                    ? (now < dayEnd ? now : dayEnd)
                    : checkOutLocal;

                const barStart = checkInLocal < dayStart ? dayStart : checkInLocal;
                const barEnd = effectiveEnd > dayEnd ? dayEnd : effectiveEnd;

                const startHourFrac = Math.max(0, (barStart.hour + barStart.minute / 60 + barStart.second / 3600));
                let endHourFrac = Math.min(24, (barEnd.hour + barEnd.minute / 60 + barEnd.second / 3600));
                
                if (barEnd.hasSame(dayEnd, "day") && barEnd.hour === 23 && barEnd.minute === 59) {
                    endHourFrac = 24;
                }

                const leftPercent = (startHourFrac / 24) * 100;
                let widthPercent = Math.max(0.15, ((endHourFrac - startHourFrac) / 24) * 100);

                let durationMs = (checkOutLocal || now).diff(checkInLocal).milliseconds;
                if (durationMs < 0) durationMs = 0;
                const hoursVal = Math.floor(durationMs / (1000 * 60 * 60));
                const minsVal = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
                const durationLabel = `${hoursVal}h ${minsVal.toString().padStart(2, "0")}m`;

                const timeRangeLabel = `${checkInLocal.toFormat("hh:mm a")} - ${isOngoing ? "Now" : checkOutLocal.toFormat("hh:mm a")}`;
                const shortRangeLabel = `${checkInLocal.toFormat("HH:mm")} - ${isOngoing ? "Now" : checkOutLocal.toFormat("HH:mm")}`;

                const hasAnomaly = att.is_anomaly || this.anomaliesMap.has(att.id);

                return {
                    id: att.id,
                    employeeId: att.employee_id[0],
                    employeeName: att.employee_id[1],
                    checkIn: att.check_in,
                    checkOut: att.check_out,
                    checkInLocal,
                    checkOutLocal,
                    isOngoing,
                    leftPercent,
                    widthPercent,
                    durationLabel,
                    timeRangeLabel,
                    shortRangeLabel,
                    hasAnomaly,
                    workedHours: att.worked_hours || (durationMs / (1000 * 60 * 60)),
                };
            });

            this.employees = employeesData.map((emp) => {
                const empAtts = processedAttendances.filter((a) => a.employeeId === emp.id);

                let totalWorkedSec = 0;
                for (const att of empAtts) {
                    const start = att.checkInLocal < dayStart ? dayStart : att.checkInLocal;
                    const end = att.isOngoing
                        ? (now < dayEnd ? now : dayEnd)
                        : (att.checkOutLocal > dayEnd ? dayEnd : att.checkOutLocal);
                    const dur = Math.max(0, end.diff(start).milliseconds);
                    totalWorkedSec += dur / 1000;
                }

                const totalWorkedHours = totalWorkedSec / 3600;
                const h = Math.floor(totalWorkedHours);
                const m = Math.floor((totalWorkedHours - h) * 60);
                const workedLabel = `${h}h ${m.toString().padStart(2, "0")}m`;

                const expectedHours = 8.0;
                const progressPercent = Math.min(100, Math.round((totalWorkedHours / expectedHours) * 100));

                return {
                    id: emp.id,
                    name: emp.name,
                    displayName: emp.display_name,
                    avatarUrl: `/web/image?model=hr.employee&id=${emp.id}&field=avatar_128`,
                    calendarName: emp.resource_calendar_id ? emp.resource_calendar_id[1] : "Standard 8h",
                    workedHours: totalWorkedHours,
                    workedLabel,
                    expectedHours,
                    progressPercent,
                    attendances: empAtts,
                };
            });

            this.attendances = processedAttendances;

        } catch (error) {
            console.error("Failed to load Attendance Timeline data:", error);
        } finally {
            this.isLoading = false;
        }
    }

    _extractEmployeeDomain(domain) {
        const empDomain = [];
        for (const leaf of domain) {
            if (Array.isArray(leaf) && leaf[0]) {
                if (leaf[0] === "employee_id" || leaf[0].startsWith("employee_id.")) {
                    const fieldName = leaf[0] === "employee_id" ? "id" : leaf[0].replace("employee_id.", "");
                    empDomain.push([fieldName, leaf[1], leaf[2]]);
                } else if (leaf[0] === "department_id") {
                    empDomain.push(["department_id", leaf[1], leaf[2]]);
                }
            }
        }
        return empDomain;
    }

    setDate(newDate) {
        this.currentDate = newDate;
        return this.load();
    }

    prevDay() {
        return this.setDate(this.currentDate.minus({ days: 1 }));
    }

    nextDay() {
        return this.setDate(this.currentDate.plus({ days: 1 }));
    }

    today() {
        const DateTime = getDateTime();
        return this.setDate(DateTime ? DateTime.now().startOf("day") : null);
    }

    setViewMode(mode) {
        this.viewMode = mode;
    }
}

// 2. RENDERER COMPONENT
export class AttendanceTimelineRenderer extends Component {
    static template = "hudson_attendance_timeline.AttendanceTimelineRenderer";
    static props = {
        employees: Array,
        currentDate: Object,
        viewMode: String,
        onCellClick: Function,
        onDragCreate: Function,
        onBarClick: Function,
    };

    setup() {
        this.leftPanelRef = useRef("leftPanel");
        this.rightPanelRef = useRef("rightPanel");

        this.dragState = {
            isDragging: false,
            pointerDown: false,
            startX: 0,
            startY: 0,
            currentX: 0,
            employeeId: null,
            gridRect: null,
        };

        const DateTime = getDateTime();
        this.hours = Array.from({ length: 24 }, (_, i) => {
            const date = DateTime ? DateTime.now().startOf("day").set({ hour: i }) : null;
            return {
                hour: i,
                label: date ? date.toFormat("h a") : `${i}:00`,
                shortLabel: date ? date.toFormat("ha") : `${i}`,
            };
        });

        this.onScrollSync = this.onScrollSync.bind(this);
        this.onRowPointerDown = this.onRowPointerDown.bind(this);
        this.onPointerMove = this.onPointerMove.bind(this);
        this.onPointerUp = this.onPointerUp.bind(this);
        this.onBarClick = this.onBarClick.bind(this);

        onMounted(() => {
            window.addEventListener("pointermove", this.onPointerMove);
            window.addEventListener("pointerup", this.onPointerUp);
        });

        onWillUnmount(() => {
            window.removeEventListener("pointermove", this.onPointerMove);
            window.removeEventListener("pointerup", this.onPointerUp);
        });
    }

    onScrollSync(ev) {
        const source = ev.target;
        if (source === this.leftPanelRef.el && this.rightPanelRef.el) {
            this.rightPanelRef.el.scrollTop = source.scrollTop;
        } else if (source === this.rightPanelRef.el && this.leftPanelRef.el) {
            this.leftPanelRef.el.scrollTop = source.scrollTop;
        }
    }

    onRowPointerDown(ev) {
        if (ev.target.closest(".o_attendance_bar")) {
            return;
        }

        const rowEl = ev.currentTarget;
        const empIdAttr = rowEl.getAttribute("data-emp-id");
        if (!empIdAttr) return;

        const employeeId = parseInt(empIdAttr, 10);
        const gridRow = rowEl.querySelector(".o_timeline_grid_row_inner");
        if (!gridRow) return;

        const rect = gridRow.getBoundingClientRect();
        this.dragState = {
            isDragging: false,
            pointerDown: true,
            startX: ev.clientX,
            startY: ev.clientY,
            currentX: ev.clientX,
            employeeId,
            gridRect: rect,
        };
    }

    onPointerMove(ev) {
        if (!this.dragState.pointerDown) return;

        const dx = Math.abs(ev.clientX - this.dragState.startX);
        const dy = Math.abs(ev.clientY - this.dragState.startY);

        if (!this.dragState.isDragging && (dx > 5 || dy > 5)) {
            this.dragState.isDragging = true;
        }

        if (this.dragState.isDragging) {
            this.dragState.currentX = ev.clientX;
            this.renderDragSelectionOverlay();
        }
    }

    onPointerUp(ev) {
        if (!this.dragState.pointerDown) return;

        const { isDragging, startX, currentX, employeeId, gridRect } = this.dragState;
        this.dragState.pointerDown = false;
        this.removeDragSelectionOverlay();

        if (isDragging && gridRect && this.props.currentDate) {
            const minX = Math.min(startX, currentX) - gridRect.left;
            const maxX = Math.max(startX, currentX) - gridRect.left;

            const startRatio = Math.max(0, Math.min(1, minX / gridRect.width));
            const endRatio = Math.max(0, Math.min(1, maxX / gridRect.width));

            const startHourDec = startRatio * 24;
            const endHourDec = endRatio * 24;

            const snappedStart = this.snapToMinutes(startHourDec, 5);
            let snappedEnd = this.snapToMinutes(endHourDec, 5);

            if (snappedEnd <= snappedStart) {
                snappedEnd = snappedStart + (5 / 60);
            }

            const checkInDT = this.props.currentDate.startOf("day").plus({ hours: snappedStart });
            let checkOutDT = this.props.currentDate.startOf("day").plus({ hours: snappedEnd });

            if (snappedEnd >= 24) {
                checkOutDT = this.props.currentDate.endOf("day");
            }

            this.props.onDragCreate({
                employeeId,
                checkIn: checkInDT.toUTC().toFormat("yyyy-MM-dd HH:mm:ss"),
                checkOut: checkOutDT.toUTC().toFormat("yyyy-MM-dd HH:mm:ss"),
            });
        } else if (!isDragging && gridRect && this.props.currentDate) {
            const clickX = ev.clientX - gridRect.left;
            const ratio = Math.max(0, Math.min(1, clickX / gridRect.width));
            const hourDec = ratio * 24;
            const snappedHour = this.snapToMinutes(hourDec, 15);

            const checkInDT = this.props.currentDate.startOf("day").plus({ hours: snappedHour });

            this.props.onCellClick({
                employeeId,
                checkIn: checkInDT.toUTC().toFormat("yyyy-MM-dd HH:mm:ss"),
            });
        }

        this.dragState.isDragging = false;
    }

    snapToMinutes(decimalHours, stepMinutes) {
        const totalMinutes = decimalHours * 60;
        const snapped = Math.round(totalMinutes / stepMinutes) * stepMinutes;
        return snapped / 60;
    }

    renderDragSelectionOverlay() {
        let overlay = document.getElementById("o_timeline_drag_overlay");
        if (!overlay) {
            overlay = document.createElement("div");
            overlay.id = "o_timeline_drag_overlay";
            overlay.className = "o_timeline_drag_overlay";
            document.body.appendChild(overlay);
        }

        const { startX, currentX, gridRect } = this.dragState;
        if (!gridRect) return;

        const left = Math.max(gridRect.left, Math.min(startX, currentX));
        const right = Math.min(gridRect.right, Math.max(startX, currentX));
        const width = Math.max(4, right - left);

        overlay.style.position = "fixed";
        overlay.style.top = `${gridRect.top}px`;
        overlay.style.left = `${left}px`;
        overlay.style.width = `${width}px`;
        overlay.style.height = `${gridRect.height}px`;
        overlay.style.display = "block";
    }

    removeDragSelectionOverlay() {
        const overlay = document.getElementById("o_timeline_drag_overlay");
        if (overlay) {
            overlay.style.display = "none";
        }
    }

    onBarClick(ev) {
        ev.stopPropagation();
        const barEl = ev.currentTarget;
        const attIdAttr = barEl.getAttribute("data-att-id");
        if (attIdAttr) {
            this.props.onBarClick(parseInt(attIdAttr, 10));
        }
    }
}

// 3. CONTROLLER COMPONENT
export class AttendanceTimelineController extends Component {
    static template = "hudson_attendance_timeline.AttendanceTimelineController";
    static props = {
        model: Object,
        Renderer: Function,
        archInfo: Object,
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.model = this.props.model;
        this.state = useState({
            dateTitle: "",
            viewMode: "day",
            isFullscreen: false,
        });

        useSubEnv({
            config: {
                ...this.env.config,
                display: {
                    controlPanel: false,
                },
            },
        });

        onWillStart(async () => {
            await this.model.load();
            this.updateDateTitle();
        });
    }

    updateDateTitle() {
        if (this.model.currentDate) {
            this.state.dateTitle = this.model.currentDate.toFormat("EEEE, dd MMMM yyyy");
        }
    }

    async onPrevDay() {
        await this.model.prevDay();
        this.updateDateTitle();
    }

    async onNextDay() {
        await this.model.nextDay();
        this.updateDateTitle();
    }

    async onToday() {
        await this.model.today();
        this.updateDateTitle();
    }

    onSetViewMode(mode) {
        this.state.viewMode = mode;
        this.model.setViewMode(mode);
        if (mode !== "day") {
            this.notification.add(
                `View mode '${mode.toUpperCase()}' is in placeholder view. Day view is fully functional.`,
                { type: "info" }
            );
        }
    }

    selectDayView() {
        this.onSetViewMode("day");
    }

    selectWeekView() {
        this.onSetViewMode("week");
    }

    selectMonthView() {
        this.onSetViewMode("month");
    }

    toggleFullscreen() {
        this.state.isFullscreen = !this.state.isFullscreen;
    }

    onCellClick({ employeeId, checkIn }) {
        this.openAttendanceFormDialog({
            employeeId,
            checkIn,
            checkOut: false,
        });
    }

    onDragCreate({ employeeId, checkIn, checkOut }) {
        this.openAttendanceFormDialog({
            employeeId,
            checkIn,
            checkOut,
        });
    }

    onBarClick(attendanceId) {
        this.openAttendanceFormDialog({
            resId: attendanceId,
        });
    }

    openAttendanceFormDialog({ employeeId, checkIn, checkOut, resId }) {
        const context = {};
        if (employeeId) context.default_employee_id = employeeId;
        if (checkIn) context.default_check_in = checkIn;
        if (checkOut) context.default_check_out = checkOut;

        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "hr.attendance",
                res_id: resId || false,
                views: [[false, "form"]],
                target: "new",
                context,
            },
            {
                onClose: async () => {
                    await this.model.load();
                },
            }
        );
    }
}

// 4. ARCH PARSER & VIEW DEFINITION
class AttendanceTimelineArchParser {
    parse(arch) {
        return {
            arch,
        };
    }
}

export const attendanceTimelineView = {
    type: "attendance_timeline",
    display_name: "Attendance Timeline",
    icon: "fa-clock-o",
    multiRecord: true,
    Controller: AttendanceTimelineController,
    Renderer: AttendanceTimelineRenderer,
    Model: AttendanceTimelineModel,
    ArchParser: AttendanceTimelineArchParser,

    props(genericProps, view) {
        const { ArchParser } = view;
        const archInfo = new ArchParser().parse(genericProps.arch);

        return {
            ...genericProps,
            archInfo,
            Model: view.Model,
            Renderer: view.Renderer,
            model: new view.Model(genericProps, genericProps.services),
        };
    },
};

registry.category("views").add("attendance_timeline", attendanceTimelineView);
