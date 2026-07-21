/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DynamicFinancialReport extends Component {
    static template = "hudson_dynamic_financial_view.DynamicFinancialReportTemplate";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            reportName: "",
            reportLines: [],
            collapsedIds: {},
            debitCredit: false,
            enableFilter: false,
            currencySymbol: "$",
            hasUnposted: false,
            showUnpostedWarning: true,
            
            // Drilldown state
            showModal: false,
            drilldownLines: [],
            drilldownAccountName: "",
            
            // Loading state
            loading: true,
        });

        // Get wizard parameters from action context
        const context = this.props.action.context || {};
        this.wizardModel = context.active_model || 'financial.report';
        this.wizardId = context.active_id;

        onWillStart(async () => {
            await this.loadReportData();
        });
    }

    async loadReportData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(this.wizardModel, "get_report_data", [this.wizardId]);
            this.state.reportName = data.report_name;
            this.state.reportLines = data.report_lines;
            this.state.debitCredit = data.debit_credit;
            this.state.enableFilter = data.enable_filter;
            this.state.currencySymbol = data.currency_symbol;
            this.state.hasUnposted = data.has_unposted;
            
            // Initialize collapsed state: collapse levels >= 3 by default
            const collapsed = {};
            for (const line of data.report_lines) {
                if (line.level >= 3 && this.hasChildren(line)) {
                    collapsed[line.id] = true;
                }
            }
            this.state.collapsedIds = collapsed;
        } catch (error) {
            console.error("Error loading financial report data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    hasChildren(line) {
        const id = line.id || line.a_id;
        return this.state.reportLines.some(l => l.parent === id);
    }

    isLineVisible(line) {
        let parentId = line.parent;
        while (parentId) {
            if (this.state.collapsedIds[parentId]) {
                return false;
            }
            // Find parent line to get its parent
            const parentLine = this.state.reportLines.find(l => l.id === parentId || l.a_id === parentId);
            parentId = parentLine ? parentLine.parent : null;
        }
        return true;
    }

    toggleCollapse(line) {
        const id = line.id || line.a_id;
        if (this.state.collapsedIds[id]) {
            delete this.state.collapsedIds[id];
        } else {
            this.state.collapsedIds[id] = true;
        }
    }

    isCollapsed(line) {
        const id = line.id || line.a_id;
        return !!this.state.collapsedIds[id];
    }

    formatCurrency(value) {
        if (value === undefined || value === null) return '';
        const formatted = Math.abs(value).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        const sign = value < 0 ? '-' : '';
        return `${sign}${this.state.currencySymbol}${formatted}`;
    }

    dismissWarning() {
        this.state.showUnpostedWarning = false;
    }

    async handleLineClick(line) {
        if (line.type === 'account') {
            this.state.loading = true;
            try {
                const items = await this.orm.call(this.wizardModel, "get_drilldown_lines", [this.wizardId], {
                    line_data: line
                });
                this.state.drilldownLines = items;
                this.state.drilldownAccountName = line.name;
                this.state.showModal = true;
            } catch (error) {
                console.error("Error loading drilldown details:", error);
            } finally {
                this.state.loading = false;
            }
        }
    }

    closeModal() {
        this.state.showModal = false;
        this.state.drilldownLines = [];
        this.state.drilldownAccountName = "";
    }

    openJournalEntry(moveId) {
        this.closeModal();
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'account.move',
            res_id: moveId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    async printPDF() {
        this.state.loading = true;
        try {
            const action = await this.orm.call(this.wizardModel, 'view_report_pdf', [this.wizardId]);
            this.action.doAction(action);
        } catch (error) {
            console.error("Error printing PDF:", error);
        } finally {
            this.state.loading = false;
        }
    }

    async exportXLSX() {
        this.state.loading = true;
        try {
            const action = await this.orm.call(this.wizardModel, 'action_print_xlsx', [this.wizardId]);
            this.action.doAction(action);
        } catch (error) {
            console.error("Error exporting XLSX:", error);
        } finally {
            this.state.loading = false;
        }
    }

    goBack() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: this.wizardModel,
            res_id: this.wizardId,
            views: [[false, 'form']],
            target: 'new',
        });
    }
}

registry.category("actions").add("hudson_dynamic_financial_report", DynamicFinancialReport);
