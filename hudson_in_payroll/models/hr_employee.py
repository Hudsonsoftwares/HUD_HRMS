# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # EPF / UAN Information
    hds_in_epf_applicable = fields.Boolean(
        string="EPF Applicable",
        default=True,
        help="Enable EPF statutory deductions for this employee."
    )
    hds_in_uan = fields.Char(
        string="UAN (Universal Account Number)",
        help="12-digit EPFO Universal Account Number."
    )
    hds_in_pf_member_id = fields.Char(
        string="PF Member ID / Member Code",
        help="Establishment Member ID (e.g. MH/BAN/0012345/000/0000123)."
    )
    hds_in_pf_joining_date = fields.Date(
        string="Date of Joining PF",
        help="Date employee first enrolled in Provident Fund."
    )
    hds_in_existing_epf_member = fields.Boolean(
        string="Existing EPF Member",
        default=True,
        help="Check if employee had a prior EPF account before joining this company."
    )
    hds_in_is_international_worker = fields.Boolean(
        string="International Worker",
        default=False,
        help="Check if employee is classified as an International Worker under EPFO rules."
    )

    # EPS (Pension) Information
    hds_in_eps_applicable = fields.Boolean(
        string="EPS Applicable",
        default=True,
        help="Enable EPS statutory pension allocation (8.33%)."
    )
    hds_in_existing_eps_member = fields.Boolean(
        string="Existing EPS Member",
        default=True,
        help="Check if employee was enrolled in EPS scheme prior to 01-Sep-2014 or current joining."
    )
    hds_in_higher_pension = fields.Boolean(
        string="Opted for Higher Pension Scheme",
        default=False,
        help="Check if employee opted for higher pension scheme under SC judgment guidelines."
    )
    hds_in_pf_contribution_basis = fields.Selection([
        ('statutory_restricted', 'Statutory Restricted (₹15,000 Cap)'),
        ('actual_basic', 'Actual Basic Pay (Uncapped)'),
    ], string="PF Contribution Basis", default='statutory_restricted', required=True)

    # VPF (Voluntary Provident Fund)
    hds_in_vpf_type = fields.Selection([
        ('none', 'None'),
        ('percent', 'Percentage of Basic Pay'),
        ('fixed', 'Fixed Monthly Amount'),
    ], string="VPF Contribution Type", default='none', required=True)

    hds_in_vpf_percent = fields.Float(
        string="VPF Percentage (%)",
        help="Additional VPF percentage contributed by employee."
    )
    hds_in_vpf_amount = fields.Float(
        string="VPF Fixed Amount (₹)",
        help="Additional VPF fixed amount contributed by employee."
    )

    # ESIC Information
    hds_in_esic_applicable = fields.Boolean(
        string="ESIC Applicable",
        default=False,
        help="Enable Employees' State Insurance (ESIC) statutory compliance for this employee."
    )
    hds_in_esic_ip_number = fields.Char(
        string="ESIC IP Number",
        help="17-digit ESIC Insured Person (IP) Number."
    )
    hds_in_esic_joining_date = fields.Date(
        string="Date of Joining ESIC",
        help="Date of enrollment into ESIC."
    )
    hds_in_esic_exit_date = fields.Date(
        string="Date of Exit ESIC",
        help="Date of exit from ESIC scheme."
    )
    hds_in_esic_ip_status = fields.Selection([
        ('active', 'Active'),
        ('exempt', 'Exempt'),
        ('resigned', 'Resigned'),
        ('disabled', 'Disabled'),
    ], string="Insured Person Status", default='active', help="Current ESIC Insured Person (IP) compliance status.")

    hds_in_is_pwd = fields.Boolean(
        string="Person with Disability (PWD)",
        default=False,
        help="Indicates that the employee is eligible for the statutory ESIC PWD wage ceiling limit."
    )

    hds_in_esic_contribution_basis = fields.Char(
        string="Contribution Basis",
        readonly=True,
        default="Gross Wages (Statutory)",
        help="ESIC contribution basis is calculated on gross wages per statutory rules."
    )
    hds_in_esic_contribution_period = fields.Char(
        string="Contribution Period",
        compute='_compute_esic_contribution_period',
        store=True,
        readonly=True,
        help="Half-yearly ESIC statutory contribution period derived automatically from joining date or current date."
    )
    hds_in_esic_dispensary = fields.Char(
        string="ESIC Dispensary",
        help="Nominated ESIC Dispensary / Medical Benefit Hospital."
    )
    hds_in_esic_exit_reason = fields.Selection([
        ('wage_exceeded', 'Salary Exceeded Limit'),
        ('resigned', 'Resigned'),
        ('death', 'Death'),
        ('retired', 'Retired'),
        ('other', 'Other'),
    ], string="Reason for Exit ESIC", help="Reason for exit from ESIC coverage.")

    hds_in_employer_cost_monthly = fields.Monetary(
        string="Employer Cost (Monthly)",
        compute='_compute_hds_in_employer_cost',
        currency_field='currency_id',
        store=True,
        readonly=True,
        help="Monthly Employer Cost to Company (CTC) synced directly from active contract."
    )
    hds_in_employer_cost_annual = fields.Monetary(
        string="Employer Cost (Annual)",
        compute='_compute_hds_in_employer_cost',
        currency_field='currency_id',
        store=True,
        readonly=True,
        help="Annual Employer Cost to Company (CTC) synced directly from active contract."
    )

    hds_in_statutory_audit_count = fields.Integer(
        string="Statutory Audits Count",
        compute='_compute_hds_in_statutory_audit_count'
    )

    @api.depends('hds_in_esic_joining_date', 'hds_in_esic_applicable')
    def _compute_esic_contribution_period(self):
        today = fields.Date.today()
        for emp in self:
            if not emp.hds_in_esic_applicable:
                emp.hds_in_esic_contribution_period = False
                continue
            ref_date = emp.hds_in_esic_joining_date or today
            year = ref_date.year
            month = ref_date.month
            if 4 <= month <= 9:
                emp.hds_in_esic_contribution_period = f"April {year} – September {year}"
            elif month >= 10:
                emp.hds_in_esic_contribution_period = f"October {year} – March {year + 1}"
            else:
                emp.hds_in_esic_contribution_period = f"October {year - 1} – March {year}"

    def _evaluate_default_esic_applicable(self, gross_wage=None, eval_date=None):
        """
        Evaluates ESIC applicability based on statutory contribution period bounds and period-start wage.
        Enforces Regulation 31 continuity: Gross wage on first day of Contribution Period defines coverage.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        if not company or not company.hds_in_esic_applicable:
            return False

        from ..services.esic.contribution_period_service import ESICContributionPeriodService
        period_service = ESICContributionPeriodService(self.env)
        return period_service.is_covered_for_contribution_period(self, eval_date=eval_date)

    @api.onchange('hds_in_is_pwd', 'company_id')
    def _onchange_esic_default_triggers(self):
        """Triggered on employee form when PWD status or company changes."""
        for emp in self:
            emp.hds_in_esic_applicable = emp._evaluate_default_esic_applicable()

    @api.constrains('hds_in_esic_applicable', 'hds_in_esic_ip_number')
    def _check_esic_ip_number(self):
        for emp in self:
            if emp.hds_in_esic_applicable and emp.hds_in_esic_ip_number:
                ip_clean = emp.hds_in_esic_ip_number.strip()
                if not ip_clean.isdigit():
                    raise ValidationError(_("ESIC IP Number must contain digits only. Invalid value: '%s'") % emp.hds_in_esic_ip_number)
                if len(ip_clean) != 17:
                    raise ValidationError(_("ESIC IP Number must be exactly 17 digits. Provided length: %d digits.") % len(ip_clean))
                duplicate = self.search([
                    ('id', '!=', emp.id),
                    ('hds_in_esic_ip_number', '=', ip_clean)
                ], limit=1)
                if duplicate:
                    raise ValidationError(_("ESIC IP Number '%s' is already registered for employee '%s'. Duplicate IP numbers are not allowed.") % (ip_clean, duplicate.name))

    def _compute_hds_in_employer_cost(self):
        for emp in self:
            contracts = self.env['hr.version'].search([('employee_id', '=', emp.id)])
            active_contract = contracts.sorted(lambda c: c.date_start or fields.Date.today(), reverse=True)[0] if contracts else False
            monthly_cost = active_contract.hds_in_employer_cost_monthly if active_contract else 0.0
            emp.hds_in_employer_cost_monthly = monthly_cost
            emp.hds_in_employer_cost_annual = monthly_cost * 12.0

    def _compute_hds_in_statutory_audit_count(self):
        for emp in self:
            emp.hds_in_statutory_audit_count = self.env['hds.in.payroll.audit'].search_count([
                ('employee_id', '=', emp.id)
            ])

    def action_view_statutory_audits(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Statutory Audit Logs'),
            'res_model': 'hds.in.payroll.audit',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
