/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { rpc } from "@web/core/network/rpc";
import { isIosApp } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { actionService, ControllerNotFoundError } from "@web/webclient/actions/action_service";

patch(ActivityMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
    },

    async signInOut() {
        this.dropdown.close();

        if (!isIosApp() && navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                async ({ coords: { latitude, longitude } }) => {
                    try {
                        this.employee = await rpc("/hr_attendance/systray_check_in_out", {
                            latitude,
                            longitude,
                        });
                        this._searchReadEmployeeFill();
                    } catch (error) {
                        this.notification.add(
                            error.data?.message || _t("An error occurred during attendance change."),
                            { type: "danger" }
                        );
                    }
                },
                async () => {
                    try {
                        this.employee = await rpc("/hr_attendance/systray_check_in_out");
                        this._searchReadEmployeeFill();
                    } catch (error) {
                        this.notification.add(
                            error.data?.message || _t("An error occurred during attendance change."),
                            { type: "danger" }
                        );
                    }
                },
                { enableHighAccuracy: true }
            );
        } else {
            try {
                this.employee = await rpc("/hr_attendance/systray_check_in_out");
                this._searchReadEmployeeFill();
            } catch (error) {
                this.notification.add(
                    error.data?.message || _t("An error occurred during attendance change."),
                    { type: "danger" }
                );
            }
        }
    },
});

patch(actionService, {
    start(env) {
        const actionManager = super.start(...arguments);
        const originalRestore = actionManager.restore;
        actionManager.restore = async function (jsId) {
            try {
                return await originalRestore.apply(this, arguments);
            } catch (error) {
                if (error instanceof ControllerNotFoundError) {
                    console.warn("Gracefully handling controller restore error:", error);
                    env.bus.trigger("WEBCLIENT:LOAD_DEFAULT_APP");
                    return;
                }
                throw error;
            }
        };
        return actionManager;
    }
});
