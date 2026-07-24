# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    hds_in_include_in_pf_wage = fields.Boolean(
        string="Include in PF Wage",
        default=False,
        help="If enabled, the calculated amount of this salary rule is included when determining the employee's PF-eligible wage."
    )
