# -*- coding: utf-8 -*-
import math
from ..base import BaseStatutoryService


class ESICEmployeeCalculator(BaseStatutoryService):
    """
    Pure Python ESIC Employee deduction calculation engine.
    Statutory basis: ESI (Central) Rules 1950 Rule 51.
    Retrieves contribution rate dynamically from hr.rule.parameter ('hds_in_esic_employee_rate').
    No hardcoded rates or thresholds.
    """

    def __init__(self, env, wage_calc, validator):
        super().__init__(env)
        self.wage_calc = wage_calc
        self.validator = validator

    def compute(self, payslip):
        """
        Computes employee ESIC deduction amount.
        Returns rounded statutory deduction amount (nearest upper rupee rounding as per ESIC rules).
        """
        if not self.validator.is_esic_eligible(payslip):
            return 0.0

        esic_wage = self.wage_calc.get_esic_contributable_wage(payslip)
        if esic_wage <= 0.0:
            return 0.0

        eval_date = payslip.date_to or self.env.context.get('date')

        # Retrieve rate from hr.rule.parameter
        rate = self.get_parameter('hds_in_esic_employee_rate', date=eval_date, as_decimal=True)
        raw_deduction = esic_wage * rate
        # Statutory ESIC rounding: rounded up to nearest rupee
        return float(math.ceil(raw_deduction))
