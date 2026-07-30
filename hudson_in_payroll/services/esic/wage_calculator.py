# -*- coding: utf-8 -*-
from ..base import BaseStatutoryService
from .validator import ESICValidator


class ESICWageCalculator(BaseStatutoryService):
    """
    Pure Python ESIC Contributable Wage calculation engine.
    Calculates gross ESIC contributable wage dynamically using effective-dated rule parameters.
    """

    def __init__(self, env, localdict=None, validator=None):
        super().__init__(env)
        self.localdict = localdict
        self.validator = validator or ESICValidator(env)

    def get_applicable_ceiling(self, payslip):
        """
        Determines applicable ESIC wage ceiling dynamically from hr.rule.parameter:
        - IF Employee hds_in_is_pwd = True -> Use ESIC PWD Wage Ceiling ('hds_in_esic_pwd_wage_ceiling')
        - ELSE -> Use Standard ESIC Wage Ceiling ('hds_in_esic_wage_ceiling')
        """
        eval_date = payslip.date_to or self.env.context.get('date')
        if payslip.employee_id and payslip.employee_id.hds_in_is_pwd:
            return self.get_parameter('hds_in_esic_pwd_wage_ceiling', date=eval_date)
        return self.get_parameter('hds_in_esic_wage_ceiling', date=eval_date)

    def get_esic_contributable_wage(self, payslip):
        """
        Calculates ESIC contributable wage by evaluating active payslip localdict against applicable ceiling.
        """
        if not self.validator.is_esic_eligible(payslip):
            return 0.0

        ld = self.localdict or {}
        gross_wage = 0.0
        categories = ld.get('categories')
        if categories and hasattr(categories, 'GROSS'):
            gross_wage = float(getattr(categories, 'GROSS', 0.0) or 0.0)

        if gross_wage <= 0.0 and ld:
            rules = ld.get('rules')
            if rules:
                for rule_code in ['BASIC', 'DA', 'HRA', 'TRAVEL', 'MEAL', 'MEDICAL', 'OTHER']:
                    gross_wage += float(ld.get(rule_code, 0.0) or 0.0)

        if gross_wage <= 0.0:
            return 0.0

        # Check gross wage against effective-dated ceiling limit
        ceiling = self.get_applicable_ceiling(payslip)
        if ceiling and gross_wage > ceiling:
            return 0.0

        return gross_wage
