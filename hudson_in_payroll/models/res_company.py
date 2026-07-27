# -*- coding: utf-8 -*-
from odoo import api, fields, models


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

    # ESIC Company Configuration Fields
    hds_in_esic_applicable = fields.Boolean(
        string="Enable ESIC",
        default=True,
        help="Enable Employee State Insurance (ESIC) statutory compliance for this company."
    )
    hds_in_esic_employer_code = fields.Char(
        string="ESIC Employer Code",
        help="Enter the Employer Code allotted by the Employees' State Insurance Corporation."
    )
    hds_in_esic_registration_no = fields.Char(
        string="ESIC Registration Number",
        help="Enter the ESIC Registration Number of the company."
    )
    hds_in_esic_branch_office = fields.Char(
        string="ESIC Branch Office",
        help="Optional. Specify the ESIC Branch/Sub Office associated with this employer."
    )

    def _register_hook(self):
        """
        Execute DDL column creation during model registration hook.
        This guarantees that PostgreSQL columns exist BEFORE base module
        button_install/button_upgrade performs ORM search([]) on res.company.
        """
        super()._register_hook()
        cr = self.env.cr
        try:
            cr.execute("""
                ALTER TABLE res_company
                ADD COLUMN IF NOT EXISTS hds_in_esic_applicable boolean DEFAULT true,
                ADD COLUMN IF NOT EXISTS hds_in_esic_employer_code varchar,
                ADD COLUMN IF NOT EXISTS hds_in_esic_registration_no varchar,
                ADD COLUMN IF NOT EXISTS hds_in_esic_branch_office varchar;
            """)
        except Exception:
            pass

    def _auto_init(self):
        """
        Pre-emptively ensure ESIC columns exist in PostgreSQL res_company table
        so that base Odoo search([]) operations during web UI module upgrade
        do not raise UndefinedColumn errors.
        """
        cr = self.env.cr
        cr.execute("""
            ALTER TABLE res_company
            ADD COLUMN IF NOT EXISTS hds_in_esic_applicable boolean DEFAULT true,
            ADD COLUMN IF NOT EXISTS hds_in_esic_employer_code varchar,
            ADD COLUMN IF NOT EXISTS hds_in_esic_registration_no varchar,
            ADD COLUMN IF NOT EXISTS hds_in_esic_branch_office varchar;
        """)
        return super(ResCompany, self)._auto_init()
