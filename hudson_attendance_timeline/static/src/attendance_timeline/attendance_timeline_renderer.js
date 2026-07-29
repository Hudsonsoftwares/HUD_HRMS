/** @odoo-module **/

import { Component, useRef, onMounted, onWillUnmount } from "@odoo/owl";

function getDateTime() {
    return (window.luxon && window.luxon.DateTime) || (typeof luxon !== "undefined" && luxon.DateTime);
}

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
            const date = DateTime.now().startOf("day").set({ hour: i });
            return {
                hour: i,
                label: date.toFormat("h a"),
                shortLabel: date.toFormat("ha"),
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

        if (isDragging && gridRect) {
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
        } else if (!isDragging && gridRect) {
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
