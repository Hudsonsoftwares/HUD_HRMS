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

    def compute(self, payslip):
        employee = payslip.employee_id

        # Step 1: Check employee eligibility
        if not employee or not employee.hds_in_epf_applicable:
            return 0.0

        eval_date = payslip.date_to or fields.Date.today()

        # Step 2: Get PF contribution wage
        contribution_wage = self.wage_calc.get_pf_contribution_wage(payslip)

        # Step 3: Fetch EPF rate from Rule Parameters
        epf_rate = self.get_pf_parameter(
            'hds_in_epf_rate',
            date=eval_date,
            as_decimal=True
        )

        # Step 4: Calculate standard EPF
        base_epf = self.round_statutory(
            contribution_wage * epf_rate
        )

        # Step 5: Calculate VPF (if applicable)
        vpf_amount = 0.0

        if employee.hds_in_vpf_type == 'percent' and employee.hds_in_vpf_percent > 0:
            actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip)
            vpf_amount = self.round_statutory(
                actual_pf_wage * (employee.hds_in_vpf_percent / 100.0)
            )

        elif employee.hds_in_vpf_type == 'fixed' and employee.hds_in_vpf_amount > 0:
            vpf_amount = float(employee.hds_in_vpf_amount)

        # Step 6: Return positive amount
        return base_epf + vpf_amount
