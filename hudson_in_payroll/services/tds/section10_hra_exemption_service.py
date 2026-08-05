# -*- coding: utf-8 -*-
import logging
from odoo import fields
from ..base import BaseStatutoryService
from .tds_parameter_service import TdsParameterService

_logger = logging.getLogger(__name__)


class Section10HraExemptionResult:
    """
    Data Transfer Object representing the result of Section 10(13A) HRA Exemption calculation.
    """
    def __init__(self, actual_hra_received, annual_rent_paid, basic_salary, is_metro,
                 rent_excess_basic, basic_pct_limit, exempt_amount, taxable_hra, remarks):
        self.actual_hra_received = actual_hra_received
        self.annual_rent_paid = annual_rent_paid
        self.basic_salary = basic_salary
        self.is_metro = is_metro
        self.rent_excess_basic = rent_excess_basic
        self.basic_pct_limit = basic_pct_limit
        self.exempt_amount = exempt_amount
        self.taxable_hra = taxable_hra
        self.remarks = remarks


class Section10HraExemptionService(BaseStatutoryService):
    """
    Dedicated Exemption Calculation Service for Section 10(13A) House Rent Allowance (HRA).
    Enforces the statutory 3-way minimum formula under Indian Income Tax Act 2025:
    1. Actual HRA received from employer
    2. Rent Paid minus 10% of Basic Salary (+ DA)
    3. 50% of Basic Salary (+ DA) for Metro cities OR 40% for Non-Metro cities
    """

    def calculate_exemption(self, annual_rent_paid, actual_hra_received, annual_basic_salary, is_metro=True, eval_date=None):
        """
        Calculates statutory HRA exemption under Section 10(13A).

        :param annual_rent_paid: Float (Annual rent paid by employee)
        :param actual_hra_received: Float (Annual HRA allowance received from payroll)
        :param annual_basic_salary: Float (Annual Basic Salary + DA)
        :param is_metro: Boolean (True if accommodation is in Metro city: Delhi, Mumbai, Kolkata, Chennai)
        :param eval_date: Date (optional)
        :return: Section10HraExemptionResult
        """
        tds_param_svc = TdsParameterService(self.env)
        eval_date = eval_date or fields.Date.today()

        # Resolve effective-dated parameters via TdsParameterService
        metro_pct = tds_param_svc.get_hra_percentage(is_metro=True, eval_date=eval_date, as_decimal=True) or 0.50
        non_metro_pct = tds_param_svc.get_hra_percentage(is_metro=False, eval_date=eval_date, as_decimal=True) or 0.40
        rent_excess_pct = tds_param_svc.get_parameter('HRA_RENT_EXCESS_BASIC_PERCENT', eval_date=eval_date, as_decimal=True) or 0.10

        basic_pct = metro_pct if is_metro else non_metro_pct

        # 1. Component 1: Actual HRA Received
        comp_actual_hra = max(0.0, actual_hra_received)

        # 2. Component 2: Rent Paid - 10% of Basic Salary
        rent_excess_basic = max(0.0, annual_rent_paid - (rent_excess_pct * annual_basic_salary))

        # 3. Component 3: 50% or 40% of Basic Salary
        basic_pct_limit = max(0.0, basic_pct * annual_basic_salary)

        # Statutory Exemption = Minimum of the 3 components
        if annual_rent_paid <= 0 or annual_basic_salary <= 0:
            exempt_amount = 0.0
            remarks = "No HRA exemption: Rent paid or Basic Salary is zero."
        else:
            exempt_amount = min(comp_actual_hra, rent_excess_basic, basic_pct_limit)
            remarks = f"Section 10(13A) HRA Exemption calculated as min(Actual HRA ₹{comp_actual_hra:,.2f}, Rent Excess 10% Basic ₹{rent_excess_basic:,.2f}, {int(basic_pct*100)}% Basic ₹{basic_pct_limit:,.2f}) = ₹{exempt_amount:,.2f}."

        taxable_hra = max(0.0, comp_actual_hra - exempt_amount)

        return Section10HraExemptionResult(
            actual_hra_received=comp_actual_hra,
            annual_rent_paid=annual_rent_paid,
            basic_salary=annual_basic_salary,
            is_metro=is_metro,
            rent_excess_basic=rent_excess_basic,
            basic_pct_limit=basic_pct_limit,
            exempt_amount=exempt_amount,
            taxable_hra=taxable_hra,
            remarks=remarks
        )
