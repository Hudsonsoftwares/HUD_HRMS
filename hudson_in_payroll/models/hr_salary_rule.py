# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    hds_in_include_in_pf_wage = fields.Boolean(
        string="Include in PF Wage",
        default=False,
        help="If enabled, the calculated amount of this salary rule is included when determining the employee's PF-eligible wage."
    )
    hds_in_contributes_to_employer_cost = fields.Boolean(
        string="Contributes to Employer Cost",
        default=False,
        help="If checked, this salary rule amount will be included in the calculation of Employer Cost to Company (CTC)."
    )

    def _register_hook(self):
        super()._register_hook()
        cr = self.env.cr
        try:
            cr.execute("""
                ALTER TABLE hr_salary_rule
                ADD COLUMN IF NOT EXISTS hds_in_include_in_pf_wage boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS hds_in_contributes_to_employer_cost boolean DEFAULT false;
            """)
        except Exception:
            pass

    def _auto_init(self):
        cr = self.env.cr
        cr.execute("""
            ALTER TABLE hr_salary_rule
            ADD COLUMN IF NOT EXISTS hds_in_include_in_pf_wage boolean DEFAULT false,
            ADD COLUMN IF NOT EXISTS hds_in_contributes_to_employer_cost boolean DEFAULT false;
        """)
        return super()._auto_init()
