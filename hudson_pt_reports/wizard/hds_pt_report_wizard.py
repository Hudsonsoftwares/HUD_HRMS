# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.fields import Date


class HdsPtReportWizard(models.TransientModel):
    """
    Unified Professional Tax (PT) Report Generator Wizard.
    Launches and filters the 14 PT statutory report types.
    """
    _name = 'hds.pt.report.wizard'
    _description = 'Professional Tax Report Generator Wizard'

    report_type = fields.Selection([
        ('register', 'Professional Tax Register'),
        ('statement', 'Employee PT Statement'),
        ('monthly_summary', 'Monthly PT Summary'),
        ('state_summary', 'State-wise PT Summary'),
        ('company_summary', 'Company-wise PT Summary'),
        ('slab_utilization', 'Salary Slab Utilization Report'),
        ('override_month', 'PT Override Month Report'),
        ('exception', 'PT Exception Report'),
        ('compliance_audit', 'PT Compliance Audit Report'),
        ('reconciliation', 'PT Reconciliation Report'),
        ('revision_impact', 'Salary Revision Impact Report'),
        ('state_mapping', 'Employee State Mapping Report'),
        ('liability_summary', 'PT Liability Summary'),
        ('config_audit', 'Professional Tax Configuration Audit'),
    ], string="Report Type", required=True, default='register')

    title = fields.Char(string="Report Title", default="Professional Tax Report")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    state_id = fields.Many2one('res.country.state', string="Work State", domain="[('country_id.code', '=', 'IN')]")
    employee_id = fields.Many2one('hr.employee', string="Employee Filter")
    date_from = fields.Date(string="From Date", default=lambda self: Date.today().replace(day=1))
    date_to = fields.Date(string="To Date", default=lambda self: Date.today())

    def action_generate_pt_report(self):
        self.ensure_one()
        # Direct user to filtered Enterprise Statutory Compliance Report view with PT preset
        action = self.env.ref('hudson_in_payroll.action_hds_in_pt_statutory_report').read()[0]
        domain = [('statutory_module', '=', 'pt')]
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        if self.date_from:
            domain.append(('calculation_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('calculation_date', '<=', self.date_to))
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))
        
        action['domain'] = domain
        action['name'] = self.title or self.report_type.replace('_', ' ').title()
        return action
