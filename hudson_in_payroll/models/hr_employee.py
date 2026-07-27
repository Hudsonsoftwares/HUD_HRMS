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
