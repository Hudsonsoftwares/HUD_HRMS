# -*- coding: utf-8 -*-
from odoo import models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    def _compute_rule(self, localdict):
        amount, quantity, rate = super()._compute_rule(localdict)
        if self.amount_select == 'code' and 'result_qty' in localdict:
            quantity = float(localdict['result_qty'])
        return amount, quantity, rate
