# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    hds_in_epf_applicable = fields.Boolean(
        string="EPF Applicable",
        help="Enable Employee Provident Fund (EPF) calculations."
    )
    hds_in_epf_employer_id = fields.Char(
        string="EPF Employer ID",
        help="Employer Establishment Code for EPF."
    )
    hds_in_eps_applicable = fields.Boolean(
        string="EPS Applicable",
        help="Enable Employee Pension Scheme (EPS) calculations."
    )
    hds_in_edli_applicable = fields.Boolean(
        string="EDLI Applicable",
        help="Enable Employee Deposit Linked Insurance (EDLI) calculations."
    )
    hds_in_edli_registration_number = fields.Char(
        string="EDLI Registration Number",
        help="Registration/Policy Number for EDLI."
    )
