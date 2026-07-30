# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HdsInSalaryRevision(models.Model):
    """
    Immutable Salary Revision History Model.
    Maintains complete historical audit records of employee salary revisions,
    statutory recalculations, and contract adjustments.
    """
    _name = 'hds.in.salary.revision'
    _description = 'Hudson Indian Payroll Salary Revision'
    _order = 'effective_date desc, id desc'

    name = fields.Char(
        string="Revision Number",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True,
        readonly=True,
        ondelete='restrict'
    )
    contract_id = fields.Many2one(
        'hr.version',
        string="Active Contract",
        required=True,
        readonly=True,
        ondelete='restrict'
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        related='employee_id.company_id',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        related='company_id.currency_id',
        readonly=True
    )
    effective_date = fields.Date(
        string="Effective Date",
        required=True,
        readonly=True
    )
    revision_type = fields.Selection([
        ('annual_increment', 'Annual Increment'),
        ('promotion', 'Promotion'),
        ('correction', 'Salary Correction'),
        ('manual', 'Manual Salary Revision'),
    ], string="Revision Type", required=True, readonly=True)

    revision_basis = fields.Selection([
        ('full_wage', 'Full Wage'),
        ('capped_wage', 'Capped Wage'),
    ], string="Applies On", required=True, readonly=True)

    capped_wage_amount = fields.Monetary(
        string="Capped Wage Amount",
        currency_field='currency_id',
        readonly=True
    )
    computation_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
    ], string="Increase Type", required=True, readonly=True)

    increase_percentage = fields.Float(
        string="Increase Percentage (%)",
        readonly=True
    )
    increase_amount = fields.Float(
        string="Increase Amount (₹)",
        readonly=True
    )

    # Salary Comparison
    old_wage = fields.Monetary(
        string="Old Gross Salary",
        currency_field='currency_id',
        readonly=True
    )
    new_wage = fields.Monetary(
        string="Revised Gross Salary",
        currency_field='currency_id',
        readonly=True
    )
    wage_difference = fields.Monetary(
        string="Gross Salary Difference",
        currency_field='currency_id',
        readonly=True
    )

    # Employer Cost (CTC)
    old_employer_cost_monthly = fields.Monetary(
        string="Old Employer Cost (Monthly)",
        currency_field='currency_id',
        readonly=True
    )
    new_employer_cost_monthly = fields.Monetary(
        string="Revised Employer Cost (Monthly)",
        currency_field='currency_id',
        readonly=True
    )

    # Statutory EPF Breakdown
    old_epf_wage = fields.Monetary(string="Old EPF Wage", currency_field='currency_id', readonly=True)
    new_epf_wage = fields.Monetary(string="Revised EPF Wage", currency_field='currency_id', readonly=True)
    old_employee_epf = fields.Monetary(string="Old Employee EPF", currency_field='currency_id', readonly=True)
    new_employee_epf = fields.Monetary(string="Revised Employee EPF", currency_field='currency_id', readonly=True)
    old_employer_pf = fields.Monetary(string="Old Employer PF", currency_field='currency_id', readonly=True)
    new_employer_pf = fields.Monetary(string="Revised Employer PF", currency_field='currency_id', readonly=True)

    # Statutory ESIC Breakdown
    old_esic_applicable = fields.Boolean(string="Old ESIC Applicable", readonly=True)
    new_esic_applicable = fields.Boolean(string="Revised ESIC Applicable", readonly=True)
    old_employee_esic = fields.Monetary(string="Old Employee ESIC", currency_field='currency_id', readonly=True)
    new_employee_esic = fields.Monetary(string="Revised Employee ESIC", currency_field='currency_id', readonly=True)
    old_employer_esic = fields.Monetary(string="Old Employer ESIC", currency_field='currency_id', readonly=True)
    new_employer_esic = fields.Monetary(string="Revised Employer ESIC", currency_field='currency_id', readonly=True)

    # Professional Tax & LWF
    old_pt_amount = fields.Monetary(string="Old PT Amount", currency_field='currency_id', readonly=True)
    new_pt_amount = fields.Monetary(string="Revised PT Amount", currency_field='currency_id', readonly=True)
    old_lwf_amount = fields.Monetary(string="Old LWF Amount", currency_field='currency_id', readonly=True)
    new_lwf_amount = fields.Monetary(string="Revised LWF Amount", currency_field='currency_id', readonly=True)

    reason = fields.Text(string="Reason for Revision", readonly=True)
    notes = fields.Text(string="Notes", readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
    ], string="Status", default='approved', readonly=True)

    created_by_id = fields.Many2one('res.users', string="Created By", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hds.in.salary.revision') or _('New')
        return super().create(vals_list)
