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
    Enforces the statutory 3-way minimum formula under Indian Income Tax Act:
    1. Actual HRA received from employer
    2. Rent Paid minus 10% of Basic Salary (+ DA)
    3. 50% of Basic Salary (+ DA) for Metro cities OR 40% for Non-Metro cities
    """

    def calculate_exemption(self, annual_rent_paid, actual_hra_received, annual_basic_salary, is_metro=True, eval_date=None, **kwargs):
        """
        Calculates statutory HRA exemption under Section 10(13A) and prints structured audit trace.

        :param annual_rent_paid: Float (Annual rent paid by employee)
        :param actual_hra_received: Float (Annual HRA allowance received from payroll)
        :param annual_basic_salary: Float (Annual Basic Salary + DA)
        :param is_metro: Boolean (True if accommodation is in Metro city: Delhi, Mumbai, Kolkata, Chennai)
        :param eval_date: Date (optional)
        :param kwargs: Optional context parameters (employee, financial_year, declaration, annual_basic_component, annual_da_component)
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
        comp_actual_hra = max(0.0, float(actual_hra_received or 0.0))

        # 2. Component 2: Rent Paid - 10% of Basic Salary
        ten_pct_salary = rent_excess_pct * float(annual_basic_salary or 0.0)
        rent_excess_basic = max(0.0, float(annual_rent_paid or 0.0) - ten_pct_salary)

        # 3. Component 3: 50% or 40% of Basic Salary
        basic_pct_limit = max(0.0, basic_pct * float(annual_basic_salary or 0.0))

        # Input Guardrails & Warnings
        missing_inputs = []
        if float(annual_basic_salary or 0.0) <= 0.0: missing_inputs.append("Annual Basic Salary (+ DA)")
        if comp_actual_hra <= 0.0: missing_inputs.append("Actual HRA Received")
        if float(annual_rent_paid or 0.0) <= 0.0: missing_inputs.append("Annual Rent Paid")

        if missing_inputs:
            _logger.warning(
                "[SECTION 10(13A) HRA WARNING] Mandatory input(s) missing or zero: %s. HRA Exemption evaluated as ₹0.00.",
                ", ".join(missing_inputs)
            )

        # Statutory Exemption = Minimum of the 3 components
        raw_rent_excess = float(annual_rent_paid or 0.0) - ten_pct_salary

        if float(annual_rent_paid or 0.0) <= 0:
            exempt_amount = 0.0
            reason = "No HRA exemption allowable: Annual Rent Paid is zero."
            remarks = "No HRA exemption: Annual Rent Paid is zero."
        elif float(annual_basic_salary or 0.0) <= 0:
            exempt_amount = 0.0
            reason = "No HRA exemption allowable: Salary considered (Basic + DA) is zero."
            remarks = "No HRA exemption: Salary considered (Basic + DA) is zero."
        else:
            exempt_amount = min(comp_actual_hra, rent_excess_basic, basic_pct_limit)
            if exempt_amount == 0.0 and raw_rent_excess <= 0.0:
                reason = f"No HRA exemption allowable because Formula 2 (Rent Paid minus 10% Salary = INR {raw_rent_excess:,.2f}) evaluated to zero after applying the statutory floor under Section 10(13A)."
            elif exempt_amount == comp_actual_hra:
                reason = f"Formula 1 (Actual HRA Received = INR {comp_actual_hra:,.2f}) is the lowest of the three statutory components under Section 10(13A)."
            elif exempt_amount == rent_excess_basic:
                reason = f"Formula 2 (Rent Paid minus 10% Salary = INR {rent_excess_basic:,.2f}) is the lowest of the three statutory components under Section 10(13A)."
            else:
                reason = f"Formula 3 (Statutory {int(basic_pct * 100)}% of Salary limit = INR {basic_pct_limit:,.2f}) is the lowest of the three statutory components under Section 10(13A)."

            remarks = f"Section 10(13A) HRA Exemption calculated as min(Actual HRA INR {comp_actual_hra:,.2f}, Rent Excess 10% Basic INR {rent_excess_basic:,.2f}, {int(basic_pct*100)}% Basic INR {basic_pct_limit:,.2f}) = INR {exempt_amount:,.2f}."

        taxable_hra = max(0.0, comp_actual_hra - exempt_amount)

        # Context Extraction for Trace Header
        employee = kwargs.get('employee')
        fy = kwargs.get('financial_year')
        decl = kwargs.get('declaration')

        emp_name = employee.name if employee else kwargs.get('employee_name', 'N/A')
        emp_id = employee.id if employee else kwargs.get('employee_id', 'N/A')
        fy_name = fy.name if fy else kwargs.get('financial_year_name', 'N/A')
        decl_id = decl.id if decl else kwargs.get('declaration_id', 'N/A')

        landlord_name = (decl.decl_hra_landlord_name if decl else False) or kwargs.get('landlord_name', 'N/A') or 'N/A'
        landlord_pan = (decl.decl_hra_landlord_pan if decl else False) or kwargs.get('landlord_pan', 'N/A') or 'N/A'

        basic_comp = kwargs.get('annual_basic_component', annual_basic_salary)
        da_comp = kwargs.get('annual_da_component', 0.0)

        # Print Structured SECTION 10(13A) HRA STATUTORY TRACE
        trace_log = f"""
=========================================================
SECTION 10(13A) HRA STATUTORY TRACE
=========================================================

Employee                : {emp_name}
Employee ID             : {emp_id}
Financial Year          : {fy_name}
Declaration ID          : {decl_id}

---------------------------------------------------------
DECLARATION INPUTS
---------------------------------------------------------

Annual Rent Paid        : INR {float(annual_rent_paid or 0.0):,.2f}
Metro City              : {"YES" if is_metro else "NO"}
Landlord Name           : {landlord_name}
Landlord PAN            : {landlord_pan}

---------------------------------------------------------
SALARY PROJECTION INPUTS
---------------------------------------------------------

Annual Basic Salary     : INR {float(basic_comp or 0.0):,.2f}
Annual Dearness Allowance : INR {float(da_comp or 0.0):,.2f}
Salary considered (Basic + DA) : INR {float(annual_basic_salary or 0.0):,.2f}

Actual HRA Received
(Current Employer)      : INR {comp_actual_hra:,.2f}

---------------------------------------------------------
STATUTORY FORMULA 1
---------------------------------------------------------

Actual HRA Received

= INR {comp_actual_hra:,.2f}

---------------------------------------------------------
STATUTORY FORMULA 2
---------------------------------------------------------

Rent Paid
= INR {float(annual_rent_paid or 0.0):,.2f}

10% of Salary
= INR {ten_pct_salary:,.2f}

Rent minus 10% Salary

= INR {rent_excess_basic:,.2f}

---------------------------------------------------------
STATUTORY FORMULA 3
---------------------------------------------------------

{"Metro Employee" if is_metro else "Non-Metro Employee"}

{int(basic_pct * 100)}% x Salary

{int(basic_pct * 100)}% x INR {float(annual_basic_salary or 0.0):,.2f}

= INR {basic_pct_limit:,.2f}

---------------------------------------------------------
LEAST OF THREE
---------------------------------------------------------

Formula 1 : INR {comp_actual_hra:,.2f}
Formula 2 : INR {rent_excess_basic:,.2f}
Formula 3 : INR {basic_pct_limit:,.2f}

Selected Exemption

= INR {exempt_amount:,.2f}

Reason

{reason}

=========================================================
FINAL HRA EXEMPTION
=========================================================

Allowed Exemption

INR {exempt_amount:,.2f}

=========================================================
"""
        _logger.warning(trace_log)

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
