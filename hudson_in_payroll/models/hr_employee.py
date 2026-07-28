# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    hds_in_epf_applicable = fields.Boolean(
        string="EPF Applicable",
        default=True,
        help="Check if Employee Provident Fund applies to this employee."
    )
    hds_in_uan = fields.Char(
        string="UAN",
        help="Universal Account Number (12 digits) issued by EPFO."
    )
    hds_in_pf_member_id = fields.Char(
        string="PF Member ID",
        help="Member ID / Member Account Number (e.g. MH/BAN/0012345/000/0000123)."
    )
    hds_in_pf_joining_date = fields.Date(
        string="PF Joining Date",
        help="Date when employee joined Provident Fund."
    )
    hds_in_existing_epf_member = fields.Boolean(
        string="Existing EPF Member",
        help="Check if employee was an existing EPF member prior to joining."
    )
    hds_in_eps_applicable = fields.Boolean(
        string="EPS Applicable",
        default=True,
        help="Check if Employee Pension Scheme applies to this employee."
    )
    hds_in_existing_eps_member = fields.Boolean(
        string="Existing EPS Member",
        help="Check if employee was an existing EPS member prior to joining."
    )
    hds_in_pf_contribution_basis = fields.Selection([
        ('statutory_ceiling', 'Statutory Wage Ceiling'),
        ('actual_basic', 'Actual PF Wage'),
    ], string="PF Contribution Basis", default='statutory_ceiling', required=True,
       help="Basis for calculating PF contribution (capped at statutory wage ceiling vs actual PF wage).")
    hds_in_higher_pension = fields.Boolean(
        string="Opted for Higher Pension",
        default=False,
        help="Opted for EPS contribution on actual basic/PF wage per Supreme Court 2022 judgment."
    )
    hds_in_is_international_worker = fields.Boolean(
        string="Is International Worker",
        default=False,
        help="International workers have no statutory wage ceiling cap."
    )
    hds_in_vpf_type = fields.Selection([
        ('none', 'None'),
        ('percent', 'Percentage of PF Wage'),
        ('fixed', 'Fixed Monthly Amount'),
    ], string="VPF Contribution Type", default='none', required=True,
       help="Voluntary Provident Fund contribution type.")
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
        string="ESIC Applicable"
    )
    hds_in_esic_ip_number = fields.Char(
        string="ESIC IP Number"
    )
    hds_in_esic_joining_date = fields.Date(
        string="Date of Joining ESIC"
    )
    hds_in_esic_exit_date = fields.Date(
        string="Date of Exit ESIC"
    )
    hds_in_esic_ip_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string="Insured Person Status")
    hds_in_esic_contribution_basis = fields.Char(
        string="Contribution Basis",
        readonly=True,
        default="Gross Wages (Statutory)"
    )
    hds_in_esic_contribution_period = fields.Char(
        string="Contribution Period"
    )
    hds_in_esic_dispensary = fields.Char(
        string="ESIC Dispensary"
    )
    hds_in_esic_exit_reason = fields.Selection([
        ('wage_exceeded', 'Salary Exceeded Limit'),
        ('resigned', 'Resigned'),
        ('death', 'Death'),
        ('retired', 'Retired'),
        ('other', 'Other'),
    ], string="Reason for Exit ESIC")

    hds_in_statutory_audit_count = fields.Integer(
        string="Statutory Audits",
        compute='_compute_hds_in_statutory_audit_count'
    )

    def _compute_hds_in_statutory_audit_count(self):
        audit_data = self.env['hds.in.payroll.audit'].read_group(
            [('employee_id', 'in', self.ids)],
            ['employee_id'],
            ['employee_id']
        )
        mapped_data = {data['employee_id'][0]: data['employee_id_count'] for data in audit_data}
        for emp in self:
            emp.hds_in_statutory_audit_count = mapped_data.get(emp.id, 0)

    def action_view_statutory_audits(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hudson_in_payroll.hds_in_payroll_audit_action")
        action['domain'] = [('employee_id', '=', self.id)]
        action['context'] = {'default_employee_id': self.id}
        return action

    def _register_hook(self):
        """
        Execute DDL column creation during model registration hook.
        Guarantees PostgreSQL columns exist BEFORE base module web search/read execution.
        """
        super()._register_hook()
        cr = self.env.cr
        try:
            cr.execute("""
                ALTER TABLE hr_employee
                ADD COLUMN IF NOT EXISTS hds_in_epf_applicable boolean DEFAULT true,
                ADD COLUMN IF NOT EXISTS hds_in_uan varchar,
                ADD COLUMN IF NOT EXISTS hds_in_pf_member_id varchar,
                ADD COLUMN IF NOT EXISTS hds_in_pf_joining_date date,
                ADD COLUMN IF NOT EXISTS hds_in_existing_epf_member boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS hds_in_eps_applicable boolean DEFAULT true,
                ADD COLUMN IF NOT EXISTS hds_in_existing_eps_member boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS hds_in_pf_contribution_basis varchar DEFAULT 'statutory_ceiling',
                ADD COLUMN IF NOT EXISTS hds_in_higher_pension boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS hds_in_is_international_worker boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS hds_in_vpf_type varchar DEFAULT 'none',
                ADD COLUMN IF NOT EXISTS hds_in_vpf_percent double precision DEFAULT 0.0,
                ADD COLUMN IF NOT EXISTS hds_in_vpf_amount double precision DEFAULT 0.0;
            """)
        except Exception:
            pass

    def _auto_init(self):
        """Pre-emptively ensure EPF fields exist in PostgreSQL hr_employee table."""
        cr = self.env.cr
        cr.execute("""
            ALTER TABLE hr_employee
            ADD COLUMN IF NOT EXISTS hds_in_epf_applicable boolean DEFAULT true,
            ADD COLUMN IF NOT EXISTS hds_in_uan varchar,
            ADD COLUMN IF NOT EXISTS hds_in_pf_member_id varchar,
            ADD COLUMN IF NOT EXISTS hds_in_pf_joining_date date,
            ADD COLUMN IF NOT EXISTS hds_in_existing_epf_member boolean DEFAULT false,
            ADD COLUMN IF NOT EXISTS hds_in_eps_applicable boolean DEFAULT true,
            ADD COLUMN IF NOT EXISTS hds_in_existing_eps_member boolean DEFAULT false,
            ADD COLUMN IF NOT EXISTS hds_in_pf_contribution_basis varchar DEFAULT 'statutory_ceiling',
            ADD COLUMN IF NOT EXISTS hds_in_higher_pension boolean DEFAULT false,
            ADD COLUMN IF NOT EXISTS hds_in_is_international_worker boolean DEFAULT false,
            ADD COLUMN IF NOT EXISTS hds_in_vpf_type varchar DEFAULT 'none',
            ADD COLUMN IF NOT EXISTS hds_in_vpf_percent double precision DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS hds_in_vpf_amount double precision DEFAULT 0.0;
        """)
        return super()._auto_init()
