/** @odoo-module **/

import { registry } from "@web/core/registry";
import { AttendanceTimelineController } from "@hudson_attendance_timeline/attendance_timeline/attendance_timeline_controller";
import { AttendanceTimelineModel } from "@hudson_attendance_timeline/attendance_timeline/attendance_timeline_model";
import { AttendanceTimelineRenderer } from "@hudson_attendance_timeline/attendance_timeline/attendance_timeline_renderer";

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
