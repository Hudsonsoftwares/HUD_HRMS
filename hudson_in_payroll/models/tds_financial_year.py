# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TdsFinancialYear(models.Model):
    """
    TDS Financial Year Master Model.
    Manages Indian Income Tax Financial Years (e.g. FY 2025-26) and Assessment Years (e.g. AY 2026-27).
    Serves as the root master linking income tax slabs, surcharge slabs, and default company tax years.
    """
    _name = 'tds.financial.year'
    _description = 'TDS Financial Year'
    _order = 'code desc, id desc'

    name = fields.Char(
        string="Financial Year Name",
        required=True,
        help="e.g. FY 2025-26 (AY 2026-27)"
    )
    code = fields.Char(
        string="Financial Year Code",
        required=True,
        help="e.g. 2025-2026"
    )
    assessment_year = fields.Char(
        string="Assessment Year",
        required=True,
        help="e.g. 2026-2027"
    )
    start_date = fields.Date(
        string="Start Date",
        required=True,
        help="Start date of the financial year (e.g. 01/04/2025)"
    )
    end_date = fields.Date(
        string="End Date",
        required=True,
        help="End date of the financial year (e.g. 31/03/2026)"
    )
    is_closed = fields.Boolean(
        string="Closed",
        default=False,
        help="Mark as true once the financial year is officially closed for tax declarations and payroll processing."
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        help="Set to false to archive old financial years."
    )
    tax_slab_ids = fields.One2many(
        'tds.tax.slab',
        'financial_year_id',
        string="Income Tax Slabs"
    )
    surcharge_ids = fields.One2many(
        'tds.surcharge',
        'financial_year_id',
        string="Surcharge Slabs"
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The Financial Year Code must be unique!')
    ]

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.start_date >= rec.end_date:
                raise ValidationError(_("Financial Year Start Date (%s) must be earlier than End Date (%s).") % (
                    rec.start_date, rec.end_date
                ))

    def write(self, vals):
        for rec in self:
            if rec.is_closed and 'is_closed' not in vals:
                raise ValidationError(_("Financial Year '%s' is closed and locked. Reopen the Financial Year to make statutory modifications.") % rec.name)
        return super(TdsFinancialYear, self).write(vals)

    def action_close_financial_year(self):
        for rec in self:
            rec.write({'is_closed': True})
            if 'hds.in.payroll.audit' in self.env:
                self.env['hds.in.payroll.audit'].create({
                    'name': f"Financial Year Closed: {rec.name}",
                    'company_id': self.env.company.id,
                    'audit_type': 'status_change',
                    'action_taken': f"Financial Year {rec.name} closed and locked against structural edits.",
                })

    def action_unclose_financial_year(self):
        for rec in self:
            rec.write({'is_closed': False})
            if 'hds.in.payroll.audit' in self.env:
                self.env['hds.in.payroll.audit'].create({
                    'name': f"Financial Year Reopened: {rec.name}",
                    'company_id': self.env.company.id,
                    'audit_type': 'status_change',
                    'action_taken': f"Financial Year {rec.name} reopened for administrative modifications.",
                })

