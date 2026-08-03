# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

MONTH_SELECTION = [
    ('1', 'January'),
    ('2', 'February'),
    ('3', 'March'),
    ('4', 'April'),
    ('5', 'May'),
    ('6', 'June'),
    ('7', 'July'),
    ('8', 'August'),
    ('9', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December'),
]


class PtPeriodSchedule(models.Model):
    """
    Master Configuration Model for Professional Tax Period Schedules.
    Single Source of Truth for Professional Tax deduction timing, statutory aggregation windows,
    and period resolution. Decoupled from salary range tax amount slabs (pt.state.slab).
    """
    _name = 'pt.period.schedule'
    _description = 'Professional Tax Period Schedule'
    _order = 'state_id, periodicity, window_start_month, date_from desc, id desc'

    name = fields.Char(
        string="Schedule Name",
        compute="_compute_name",
        store=True,
        help="Automated descriptive name summarizing state, periodicity, aggregation window, and deduction strategy."
    )
    state_id = fields.Many2one(
        'res.country.state',
        string="State",
        required=True,
        domain="[('country_id.code', '=', 'IN')]",
        help="Applicable Indian State for this Professional Tax period schedule."
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company Scope",
        default=lambda self: self.env.company,
        help="Optional company-specific override. Leave blank for global state default."
    )
    periodicity = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half-Yearly'),
        ('annual', 'Annual'),
    ], string="Periodicity", default='monthly', required=True,
        help="Statutory periodicity for Professional Tax calculation and reporting.")

    window_start_month = fields.Selection(
        MONTH_SELECTION,
        string="Window Start Month",
        default='4',
        required=True,
        help="Calendar month when statutory wage aggregation window starts (e.g. 4 for April in H1, 10 for October in H2)."
    )
    window_end_month = fields.Selection(
        MONTH_SELECTION,
        string="Window End Month",
        default='3',
        required=True,
        help="Calendar month when statutory wage aggregation window ends (e.g. 9 for September in H1, 3 for March in H2)."
    )

    deduction_strategy = fields.Selection([
        ('every_payroll', 'Every Payroll'),
        ('end_of_period', 'End of Period'),
        ('beginning_of_period', 'Beginning of Period'),
        ('specific_month', 'Specific Month'),
    ], string="Deduction Strategy", default='every_payroll', required=True,
        help="Strategy determining when Professional Tax is deducted from payslips during the period.")

    deduction_month = fields.Selection(
        MONTH_SELECTION,
        string="Deduction Month",
        required=False,
        help="Calendar month in which deduction occurs when Deduction Strategy is set to 'Specific Month'."
    )

    date_from = fields.Date(
        string="Effective From",
        required=False,
        help="Start date from which this period schedule configuration is effective."
    )
    date_to = fields.Date(
        string="Effective To",
        help="Optional end date until which this period schedule configuration is effective."
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        help="Archiving flag to disable historical schedules."
    )
    remarks = fields.Text(
        string="Remarks / Statutory References",
        help="Government act reference, gazette reference, or statutory notes."
    )

    @api.depends('state_id', 'periodicity', 'window_start_month', 'window_end_month', 'deduction_strategy', 'deduction_month')
    def _compute_name(self):
        month_dict = dict(MONTH_SELECTION)
        strat_dict = dict([
            ('every_payroll', 'Every Payroll'),
            ('end_of_period', 'End of Period'),
            ('beginning_of_period', 'Beginning of Period'),
            ('specific_month', 'Specific Month'),
        ])
        for rec in self:
            st_name = rec.state_id.name if rec.state_id else 'Global'
            per_name = (rec.periodicity or 'monthly').replace('_', '-').title()
            start_m = month_dict.get(rec.window_start_month, '')
            end_m = month_dict.get(rec.window_end_month, '')
            strat = strat_dict.get(rec.deduction_strategy, '')
            rec.name = f"{st_name} {per_name} ({start_m}–{end_m}) - {strat}"

    @api.constrains('date_from', 'date_to')
    def _check_effective_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_("Effective From date (%s) cannot be later than Effective To date (%s).") % (rec.date_from, rec.date_to))
