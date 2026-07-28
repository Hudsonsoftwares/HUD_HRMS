# -*- coding: utf-8 -*-
from odoo import fields
from ..base import BaseStatutoryService


class EPFEmployeeCalculator(BaseStatutoryService):
    """
    Calculates Employee EPF Contribution (Standard EPF + VPF).
    Returns POSITIVE float amount. Negative conversion belongs strictly to HrPayslip layer.
    """

    def __init__(self, env, wage_calc):
        super().__init__(env)
        self.wage_calc = wage_calc

    def compute(self, payslip, localdict=None):
        employee = payslip.employee_id

        print("===== EMPLOYEE EPF DEBUG =====")
        print("Employee:", employee.name if employee else None)
        print("EPF Applicable:", employee.hds_in_epf_applicable if employee else None)

        if not employee or not employee.hds_in_epf_applicable:
            print("Returning 0 because employee is not EPF applicable")
            return 0.0

        eval_date = payslip.date_to or fields.Date.today()

        contribution_wage = self.wage_calc.get_pf_contribution_wage(
            payslip,
            localdict=localdict
        )
        print("Contribution Wage:", contribution_wage)

        epf_rate = self.get_pf_parameter(
            'EPF_RATE',
            date=eval_date,
            as_decimal=True
        )
        print("EPF Rate:", epf_rate)

        raw_epf = contribution_wage * epf_rate
        print("Raw EPF:", raw_epf)

        base_epf = self.round_statutory(raw_epf)
        print("Rounded EPF:", base_epf)

        return base_epf
        
