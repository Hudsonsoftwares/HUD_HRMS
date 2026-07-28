# -*- coding: utf-8 -*-
from odoo import fields
from ..base import BaseStatutoryService


class EPFEmployerCalculator(BaseStatutoryService):
    """Calculates Employer EPF Share, EDLI, and Admin Charges."""

    def __init__(self, env, wage_calc, pension_calc):
        super().__init__(env)
        self.wage_calc = wage_calc
        self.pension_calc = pension_calc

    def compute_employer_epf(self, payslip, localdict=None):
        employee = payslip.employee_id
        if not employee.hds_in_epf_applicable:
            return 0.0

        eval_date = payslip.date_to or fields.Date.today()
        pf_wage = self.wage_calc.get_pf_contribution_wage(payslip, localdict=localdict)
        employer_epf_rate = self.get_pf_parameter('EMPLOYER_EPF_RATE', date=eval_date, as_decimal=True)

        total_statutory = self.round_statutory(pf_wage * employer_epf_rate)
        eps_amount = self.pension_calc.compute(payslip, localdict=localdict)

        return max(0.0, total_statutory - eps_amount)

    def compute_edli(self, payslip, localdict=None):
        employee = payslip.employee_id
        if not employee.hds_in_epf_applicable:
            return 0.0

        eval_date = payslip.date_to or fields.Date.today()
        actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip, localdict=localdict)

        if employee.hds_in_is_international_worker:
            edli_wage = actual_pf_wage
        else:
            edli_ceiling = self.get_pf_parameter('EDLI_WAGE_CEILING', date=eval_date)
            edli_wage = min(actual_pf_wage, edli_ceiling)

        edli_rate = self.get_pf_parameter('EDLI_RATE', date=eval_date, as_decimal=True)
        return self.round_statutory(edli_wage * edli_rate)

    def compute_epf_admin(self, payslip, localdict=None):
        employee = payslip.employee_id
        if not employee.hds_in_epf_applicable:
            return 0.0

        eval_date = payslip.date_to or fields.Date.today()
        pf_wage = self.wage_calc.get_pf_contribution_wage(payslip, localdict=localdict)
        admin_rate = self.get_pf_parameter('EPF_ADMIN_RATE', date=eval_date, as_decimal=True)
        return self.round_statutory(pf_wage * admin_rate)

    def compute_edli_admin(self, payslip, localdict=None):
        employee = payslip.employee_id
        if not employee.hds_in_epf_applicable:
            return 0.0

        eval_date = payslip.date_to or fields.Date.today()
        actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip, localdict=localdict)

        if employee.hds_in_is_international_worker:
            edli_wage = actual_pf_wage
        else:
            edli_ceiling = self.get_pf_parameter('EDLI_WAGE_CEILING', date=eval_date)
            edli_wage = min(actual_pf_wage, edli_ceiling)

        admin_rate = self.get_pf_parameter('EDLI_ADMIN_RATE', date=eval_date, as_decimal=True)
        return self.round_statutory(edli_wage * admin_rate)
