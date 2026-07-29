/** @odoo-module **/

import { Component, useSubEnv, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

export class AttendanceTimelineController extends Component {
    static template = "hudson_attendance_timeline.AttendanceTimelineController";
    static props = {
        model: Object,
        Renderer: Function,
        archInfo: Object,
    };

    setup() {
        this.dialogService = useService("dialog");
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
        this.state.dateTitle = this.model.currentDate.toFormat("EEEE, dd MMMM yyyy");
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

        this.dialogService.add(FormViewDialog, {
            resModel: "hr.attendance",
            resId: resId || false,
            context,
            title: resId ? "Edit Attendance" : "Create Attendance",
            onRecordSaved: async () => {
                await this.model.load();
            },
        });
    }
}
