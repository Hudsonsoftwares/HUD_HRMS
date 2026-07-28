# -*- coding: utf-8 -*-
from odoo import fields
from ..base import BaseStatutoryService


class EPFEmployerCalculator(BaseStatutoryService):
    """Calculates Employer EPF Total, Employer EPF Share, EPS, EDLI, and Admin Charges."""

    def __init__(self, env, wage_calc, pension_calc):
        super().__init__(env)
        self.wage_calc = wage_calc
        self.pension_calc = pension_calc

    def compute_employer_total_pf(self, payslip):
        """
        Calculates the Total Employer Statutory PF Contribution (12% of PF Wage).
        Formula: Round(PF Wage * EMPLOYER_EPF_RATE)
        Example: ₹17,000 * 12% = ₹2,040.00
        """
        employee = payslip.employee_id
        if not employee or not employee.hds_in_epf_applicable:
            return 0.0

        eval_date = payslip.date_to or fields.Date.today()
        pf_wage = self.wage_calc.get_pf_contribution_wage(payslip)
        employer_epf_rate = self.get_pf_parameter('EMPLOYER_EPF_RATE', date=eval_date, as_decimal=True)

        return self.round_statutory(pf_wage * employer_epf_rate)

    def compute_employer_epf_share(self, payslip):
        """
        Calculates the Net Employer EPF Contribution Share after deducting EPS share.
        Formula: Max(0.0, Total Employer PF Contribution - Employer EPS Contribution)
        Example: ₹2,040 (Total 12%) - ₹1,250 (EPS 8.33%) = ₹790.00
        """
        employee = payslip.employee_id
        if not employee or not employee.hds_in_epf_applicable:
            return 0.0

        total_statutory = self.compute_employer_total_pf(payslip)
        eps_amount = self.pension_calc.compute(payslip)

        return max(0.0, total_statutory - eps_amount)

    def compute_employer_epf(self, payslip):
        """
        Alias for compute_employer_epf_share() for backward compatibility.
        Returns the Net Employer EPF Share (3.67% / Remainder after EPS).
        """
        return self.compute_employer_epf_share(payslip)

    def compute_edli(self, payslip):
        employee = payslip.employee_id
        if not employee or not employee.hds_in_epf_applicable:
            return 0.0

        eval_date = payslip.date_to or fields.Date.today()
        actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip)

        if employee.hds_in_is_international_worker:
            edli_wage = actual_pf_wage
        else:
            edli_ceiling = self.get_pf_parameter('EDLI_WAGE_CEILING', date=eval_date)
            edli_wage = min(actual_pf_wage, edli_ceiling)

        edli_rate = self.get_pf_parameter('EDLI_RATE', date=eval_date, as_decimal=True)
        return self.round_statutory(edli_wage * edli_rate)

    def compute_epf_admin(self, payslip):
        employee = payslip.employee_id
        if not employee or not employee.hds_in_epf_applicable:
            return 0.0

        eval_date = payslip.date_to or fields.Date.today()
        pf_wage = self.wage_calc.get_pf_contribution_wage(payslip)
        admin_rate = self.get_pf_parameter('EPF_ADMIN_RATE', date=eval_date, as_decimal=True)
        return self.round_statutory(pf_wage * admin_rate)

    def compute_edli_admin(self, payslip):
        employee = payslip.employee_id
        if not employee or not employee.hds_in_epf_applicable:
            return 0.0

        eval_date = payslip.date_to or fields.Date.today()
        actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip)

        if employee.hds_in_is_international_worker:
            edli_wage = actual_pf_wage
        else:
            edli_ceiling = self.get_pf_parameter('EDLI_WAGE_CEILING', date=eval_date)
            edli_wage = min(actual_pf_wage, edli_ceiling)

        admin_rate = self.get_pf_parameter('EDLI_ADMIN_RATE', date=eval_date, as_decimal=True)
        return self.round_statutory(edli_wage * admin_rate)
