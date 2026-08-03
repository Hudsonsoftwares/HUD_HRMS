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
    hds_in_enable_statutory_audit = fields.Boolean(
        string="Enable Statutory Calculation Audit Logging",
        default=True,
        help="Record detailed calculation input/output/parameter audit logs for statutory compliance."
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

    # LWF Company Configuration Fields
    hds_in_enable_lwf = fields.Boolean(
        string="Enable Labour Welfare Fund (LWF)",
        default=True,
        help="Enable Labour Welfare Fund (LWF) statutory compliance for this company."
    )
    hds_in_lwf_registration_no = fields.Char(
        string="LWF Registration Number",
        help="Statutory Registration / Establishment Code under Labour Welfare Fund Act."
    )

    # Gratuity Company Configuration Fields
    hds_in_enable_gratuity = fields.Boolean(
        string="Enable Gratuity",
        default=False,
        help="Determines whether the company is covered under the Payment of Gratuity Act."
    )
    hds_in_gratuity_registration_no = fields.Char(
        string="Gratuity Registration Number",
        help="Stores the company's gratuity registration/reference number for statutory records."
    )

    # Professional Tax (PT) Company Configuration Fields
    hds_in_enable_professional_tax = fields.Boolean(
        string="Enable Professional Tax",
        default=False,
        help="Determines whether the company is liable to deduct Professional Tax."
    )
    hds_in_professional_tax_registration_no = fields.Char(
        string="Professional Tax Registration Number",
        help="Stores the company's Professional Tax Registration Number (PTRC/PTEC or equivalent, depending on the state)."
    )

    # Payroll & Bonus Management Configuration Fields
    hds_in_regular_struct_id = fields.Many2one(
        'hr.payroll.structure',
        string="Regular Payroll Structure",
        help="Default Salary Structure used for regular monthly payroll processing."
    )
    hds_in_bonus_struct_id = fields.Many2one(
        'hr.payroll.structure',
        string="Bonus Payroll Structure",
        help="Default Salary Structure used for separate bonus payroll processing."
    )
    hds_in_bonus_apply_tds = fields.Boolean(
        string="Apply TDS on Bonus",
        default=True,
        help="If checked, Tax Deducted at Source (TDS) rule applies to Bonus Payroll."
    )
    hds_in_bonus_apply_pf = fields.Boolean(
        string="Apply PF on Bonus",
        default=False,
        help="If checked, Provident Fund (PF) rule applies to Bonus Payroll."
    )
    hds_in_bonus_apply_esi = fields.Boolean(
        string="Apply ESI on Bonus",
        default=False,
        help="If checked, Employee State Insurance (ESI) rule applies to Bonus Payroll."
    )
    hds_in_bonus_apply_pt = fields.Boolean(
        string="Apply Professional Tax on Bonus",
        default=False,
        help="If checked, Professional Tax (PT) rule applies to Bonus Payroll."
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
                ADD COLUMN IF NOT EXISTS hds_in_enable_statutory_audit boolean DEFAULT true,
                ADD COLUMN IF NOT EXISTS hds_in_esic_applicable boolean DEFAULT true,
                ADD COLUMN IF NOT EXISTS hds_in_esic_employer_code varchar,
                ADD COLUMN IF NOT EXISTS hds_in_esic_registration_no varchar,
                ADD COLUMN IF NOT EXISTS hds_in_esic_branch_office varchar,
                ADD COLUMN IF NOT EXISTS hds_in_enable_lwf boolean DEFAULT true,
                ADD COLUMN IF NOT EXISTS hds_in_lwf_registration_no varchar,
                ADD COLUMN IF NOT EXISTS hds_in_enable_gratuity boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS hds_in_gratuity_registration_no varchar,
                ADD COLUMN IF NOT EXISTS hds_in_enable_professional_tax boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS hds_in_professional_tax_registration_no varchar,
                ADD COLUMN IF NOT EXISTS hds_in_regular_struct_id integer,
                ADD COLUMN IF NOT EXISTS hds_in_bonus_struct_id integer,
                ADD COLUMN IF NOT EXISTS hds_in_bonus_apply_tds boolean DEFAULT true,
                ADD COLUMN IF NOT EXISTS hds_in_bonus_apply_pf boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS hds_in_bonus_apply_esi boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS hds_in_bonus_apply_pt boolean DEFAULT false;
            """)
        except Exception:
            pass

    def _auto_init(self):
        """
        Pre-emptively ensure ESIC, LWF, Gratuity, PT and Bonus columns exist in PostgreSQL res_company table.
        """
        cr = self.env.cr
        cr.execute("""
            ALTER TABLE res_company
            ADD COLUMN IF NOT EXISTS hds_in_enable_statutory_audit boolean DEFAULT true,
            ADD COLUMN IF NOT EXISTS hds_in_esic_applicable boolean DEFAULT true,
            ADD COLUMN IF NOT EXISTS hds_in_esic_employer_code varchar,
            ADD COLUMN IF NOT EXISTS hds_in_esic_registration_no varchar,
            ADD COLUMN IF NOT EXISTS hds_in_esic_branch_office varchar,
            ADD COLUMN IF NOT EXISTS hds_in_enable_lwf boolean DEFAULT true,
            ADD COLUMN IF NOT EXISTS hds_in_lwf_registration_no varchar,
            ADD COLUMN IF NOT EXISTS hds_in_enable_gratuity boolean DEFAULT false,
            ADD COLUMN IF NOT EXISTS hds_in_gratuity_registration_no varchar,
            ADD COLUMN IF NOT EXISTS hds_in_enable_professional_tax boolean DEFAULT false,
            ADD COLUMN IF NOT EXISTS hds_in_professional_tax_registration_no varchar,
            ADD COLUMN IF NOT EXISTS hds_in_regular_struct_id integer,
            ADD COLUMN IF NOT EXISTS hds_in_bonus_struct_id integer,
            ADD COLUMN IF NOT EXISTS hds_in_bonus_apply_tds boolean DEFAULT true,
            ADD COLUMN IF NOT EXISTS hds_in_bonus_apply_pf boolean DEFAULT false,
            ADD COLUMN IF NOT EXISTS hds_in_bonus_apply_esi boolean DEFAULT false,
            ADD COLUMN IF NOT EXISTS hds_in_bonus_apply_pt boolean DEFAULT false;
        """)
        return super(ResCompany, self)._auto_init()

