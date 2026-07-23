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
        ('actual_basic', 'Actual Basic / Gross Wage'),
    ], string="PF Contribution Basis", default='statutory_ceiling', required=True,
       help="Basis for calculating PF contribution (capped at statutory ceiling vs actual basic).")
