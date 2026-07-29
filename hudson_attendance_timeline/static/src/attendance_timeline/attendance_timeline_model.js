/** @odoo-module **/

import { Reactive } from "@web/core/utils/reactive";

function getDateTime() {
    return (window.luxon && window.luxon.DateTime) || (typeof luxon !== "undefined" && luxon.DateTime);
}

export class AttendanceTimelineModel extends Reactive {
    setup(params, services) {
        this.orm = services.orm;
        this.notification = services.notification;

        const DateTime = getDateTime();
        this.currentDate = DateTime.now().startOf("day");
        this.viewMode = "day"; // "day", "week", "month"
        this.isLoading = false;

        this.employees = [];
        this.attendances = [];
        this.anomaliesMap = new Set();
        this.domain = params.domain || [];
    }

    async load(domain = this.domain) {
        const DateTime = getDateTime();
        this.domain = domain;
        this.isLoading = true;

        try {
            const dayStart = this.currentDate.startOf("day");
            const dayEnd = this.currentDate.endOf("day");

            // Format for ORM search (UTC ISO strings)
            const dayStartUTC = dayStart.toUTC().toFormat("yyyy-MM-dd HH:mm:ss");
            const dayEndUTC = dayEnd.toUTC().toFormat("yyyy-MM-dd HH:mm:ss");

            // 1. Fetch Employees
            const empFields = ["id", "name", "display_name", "resource_calendar_id"];
            const empDomain = [...this._extractEmployeeDomain(domain)];
            const employeesData = await this.orm.searchRead("hr.employee", empDomain, empFields, { order: "name asc" });

            // 2. Fetch Attendances overlapping the selected day
            const attDomain = [
                ["check_in", "<=", dayEndUTC],
                "|",
                ["check_out", ">=", dayStartUTC],
                ["check_out", "=", false],
            ];

            const attFields = ["id", "employee_id", "check_in", "check_out", "worked_hours"];

            // Add dynamic extra-hours or anomaly field if present on model
            try {
                const attendanceModelFields = await this.orm.call("hr.attendance", "fields_get", [], {});
                if (attendanceModelFields.is_anomaly) {
                    attFields.push("is_anomaly");
                }
            } catch (e) {
                // Ignore if fields_get call fails
            }

            const attData = await this.orm.searchRead("hr.attendance", attDomain, attFields);

            // 3. Fetch Anomalies if model exists
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
            } catch (e) {
                // Anomaly model optional
            }

            // 4. Process and structure data per employee
            const now = DateTime.now();

            const processedAttendances = attData.map((att) => {
                const checkInLocal = DateTime.fromSQL(att.check_in, { zone: "utc" }).toLocal();
                let checkOutLocal = att.check_out
                    ? DateTime.fromSQL(att.check_out, { zone: "utc" }).toLocal()
                    : null;

                const isOngoing = !att.check_out;

                // For ongoing attendance, end bar at min(now, dayEnd)
                const effectiveEnd = isOngoing
                    ? (now < dayEnd ? now : dayEnd)
                    : checkOutLocal;

                // Clamp to day boundaries for 24h rendering
                const barStart = checkInLocal < dayStart ? dayStart : checkInLocal;
                const barEnd = effectiveEnd > dayEnd ? dayEnd : effectiveEnd;

                // Calculate 24h timeline positions in percentages
                const startHourFrac = Math.max(0, (barStart.hour + barStart.minute / 60 + barStart.second / 3600));
                let endHourFrac = Math.min(24, (barEnd.hour + barEnd.minute / 60 + barEnd.second / 3600));
                
                // If bar spans full day or ends at midnight
                if (barEnd.hasSame(dayEnd, "day") && barEnd.hour === 23 && barEnd.minute === 59) {
                    endHourFrac = 24;
                }

                const leftPercent = (startHourFrac / 24) * 100;
                let widthPercent = Math.max(0.15, ((endHourFrac - startHourFrac) / 24) * 100);

                // Duration text
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

            // 5. Build Employee List with worked hours & expected capacity
            this.employees = employeesData.map((emp) => {
                const empAtts = processedAttendances.filter((a) => a.employeeId === emp.id);

                // Total worked hours for the visible day
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

                // Default expected working hours = 8h
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
        return this.setDate(DateTime.now().startOf("day"));
    }

    setViewMode(mode) {
        this.viewMode = mode;
    }
}
