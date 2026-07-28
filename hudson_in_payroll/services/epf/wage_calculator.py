# -*- coding: utf-8 -*-
from odoo import fields
from ..base import BaseStatutoryService


class EPFWageCalculator(BaseStatutoryService):
    """Calculates Actual PF Wage and Statutory Contribution Wage Basis."""

    def __init__(self, env, localdict=None):
        super().__init__(env)
        self.localdict = localdict

    def get_actual_pf_wage(self, payslip, localdict=None):
        """Delegates actual PF wage calculation to payslip domain API."""
        ld = localdict if localdict is not None else self.localdict
        return payslip.hds_in_get_actual_pf_wage(localdict=ld)

    def get_pf_contribution_wage(self, payslip, localdict=None):
        """
        Determines the wage basis for PF contribution.
        Capped at Statutory PF Wage Ceiling (default ₹15,000) unless:
        - Employee is an International Worker (IW)
        - Contribution basis is set to 'actual_basic' or 'actual_pf_wage'
        """
        ld = localdict if localdict is not None else self.localdict
        employee = payslip.employee_id
        actual_pf_wage = self.get_actual_pf_wage(payslip, localdict=ld)

        if employee.hds_in_is_international_worker:
            return actual_pf_wage

        if employee.hds_in_pf_contribution_basis in ('actual_basic', 'actual_pf_wage'):
            return actual_pf_wage

        eval_date = payslip.date_to or fields.Date.today()
        pf_ceiling = self.get_pf_parameter('PF_WAGE_CEILING', date=eval_date)
        return min(actual_pf_wage, pf_ceiling)
