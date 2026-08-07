# -*- coding: utf-8 -*-
import logging
from odoo import fields
from ..base import BaseStatutoryService
from .tds_parameter_service import TdsParameterService

_logger = logging.getLogger(__name__)


class Section80EEAValidationResult:
    """
    Data Transfer Object representing the audit result of a Section 80EEA statutory eligibility check.
    """
    def __init__(self, is_eligible, remarks, max_statutory_ceiling=0.0, allowed_deduction=0.0):
        self.is_eligible = is_eligible
        self.remarks = remarks
        self.max_statutory_ceiling = max_statutory_ceiling
        self.allowed_deduction = allowed_deduction

    def to_dict(self):
        return {
            'is_eligible': self.is_eligible,
            'remarks': self.remarks,
            'max_statutory_ceiling': self.max_statutory_ceiling,
            'allowed_deduction': self.allowed_deduction,
        }


class Section80EEAEligibilityService(BaseStatutoryService):
    """
    Dedicated Service Resolver for Section 80EEA Housing Loan Interest Exemption.
    Enforces statutory eligibility rules under Section 80EEA of the Income Tax Act:
    1. Permitted ONLY under Old Tax Regime.
    2. Housing loan sanctioned between 01-Apr-2019 and 31-Mar-2022.
    3. Stamp duty value of residential house property <= ₹45,00,000 (INR 45 Lakhs).
    4. Employee is a First-Time Home Buyer (does not own any residential property on loan sanction date).
    5. Assessee has NOT claimed deduction under Section 80EE.
    6. Capped at statutory ceiling of ₹1,50,000 p.a.
    """

    # Statutory date boundaries
    SECTION_80EEA_START_DATE = fields.Date.from_string('2019-04-01')
    SECTION_80EEA_END_DATE = fields.Date.from_string('2022-03-31')
    MAX_STAMP_DUTY_VALUE = 4500000.0  # ₹45 Lakhs

    def validate_eligibility(self, record_or_dict, eval_date=None, regime_code='old', **kwargs):
        """
        Validates statutory Section 80EEA eligibility for a declaration recordset or data dictionary.

        :param record_or_dict: tds.employee.declaration or tds.employee.home.loan recordset or raw dict
        :param eval_date: Date (optional)
        :param regime_code: str ('old' or 'new')
        :param kwargs: Additional context parameters (employee, financial_year)
        :return: Section80EEAValidationResult
        """
        tds_param_svc = TdsParameterService(self.env)
        eval_date = eval_date or fields.Date.today()

        # Extract values cleanly whether passed declaration header ORM record, home loan record, or dict
        if hasattr(record_or_dict, 'decl_80eea_interest'):
            # tds.employee.declaration record
            decl = record_or_dict
            employee = kwargs.get('employee') or getattr(decl, 'employee_id', False)
            fy = kwargs.get('financial_year') or getattr(decl, 'financial_year_id', False)
            regime = getattr(decl, 'regime_code', regime_code or 'old').lower()

            sanction_date = decl.decl_80eea_loan_sanction_date
            stamp_val = float(decl.decl_80eea_property_stamp_value or 0.0)
            is_first_buyer = bool(decl.decl_80eea_first_time_home_buyer)
            claimed_80ee = bool(decl.decl_80eea_claimed_under_80ee)
            claimed_amt = float(decl.decl_80eea_interest or 0.0)
            lending_inst = decl.decl_80eea_lending_institution or 'N/A'
            acct_num = decl.decl_80eea_loan_account_number or 'N/A'
            decl_id = decl.id
        elif hasattr(record_or_dict, 'loan_sanction_date'):
            # tds.employee.home.loan record
            rec = record_or_dict
            employee = kwargs.get('employee') or getattr(rec, 'employee_id', False)
            fy = kwargs.get('financial_year') or getattr(rec, 'financial_year_id', False)
            regime = (regime_code or 'old').lower()

            sanction_date = rec.loan_sanction_date
            stamp_val = float(rec.property_stamp_value or 0.0)
            is_first_buyer = bool(rec.is_first_time_home_buyer)
            claimed_80ee = bool(getattr(rec, 'claimed_under_80ee', False))
            claimed_amt = float(rec.claimed_interest_amount or 0.0)
            lending_inst = getattr(rec, 'lending_institution', 'N/A') or 'N/A'
            acct_num = getattr(rec, 'loan_account_number', 'N/A') or 'N/A'
            decl_id = rec.id
        else:
            # Raw dictionary fallback
            d = record_or_dict or {}
            employee = kwargs.get('employee')
            fy = kwargs.get('financial_year')
            regime = str(d.get('regime_code', regime_code or 'old')).lower()

            sanction_date = d.get('loan_sanction_date') or d.get('decl_80eea_loan_sanction_date')
            stamp_val = float(d.get('property_stamp_value', d.get('decl_80eea_property_stamp_value', 0.0)))
            is_first_buyer = bool(d.get('is_first_time_home_buyer', d.get('decl_80eea_first_time_home_buyer', True)))
            claimed_80ee = bool(d.get('claimed_under_80ee', d.get('decl_80eea_claimed_under_80ee', False)))
            claimed_amt = float(d.get('claimed_interest_amount', d.get('decl_80eea_interest', 0.0)))
            lending_inst = d.get('lending_institution', d.get('decl_80eea_lending_institution', 'N/A'))
            acct_num = d.get('loan_account_number', d.get('decl_80eea_loan_account_number', 'N/A'))
            decl_id = d.get('declaration_id', 'N/A')

        if isinstance(sanction_date, str):
            sanction_date = fields.Date.from_string(sanction_date)

        emp_name = employee.name if employee else kwargs.get('employee_name', 'N/A')
        emp_id = employee.id if employee else kwargs.get('employee_id', 'N/A')
        fy_name = fy.name if fy else kwargs.get('financial_year_name', 'N/A')

        max_ceiling = tds_param_svc.get_parameter('80EEA_MAX_LIMIT', eval_date=eval_date) or 150000.0

        # Evaluate Statutory Conditions
        cond_regime = (regime == 'old')
        cond_date_present = bool(sanction_date)
        cond_date_window = bool(sanction_date and self.SECTION_80EEA_START_DATE <= sanction_date <= self.SECTION_80EEA_END_DATE)
        cond_stamp_value = (stamp_val > 0.0 and stamp_val <= self.MAX_STAMP_DUTY_VALUE)
        cond_first_buyer = is_first_buyer
        cond_no_80ee = not claimed_80ee

        # Overall Eligibility
        is_eligible = (
            cond_regime and cond_date_present and cond_date_window and
            cond_stamp_value and cond_first_buyer and cond_no_80ee
        )

        if not cond_regime:
            reason = "Section 80EEA deduction is not permitted under the New Tax Regime (Section 115BAC)."
            allowed_deduction = 0.0
        elif not cond_date_present:
            reason = "Section 80EEA Ineligible: Housing Loan Sanction Date is missing."
            allowed_deduction = 0.0
        elif not cond_date_window:
            reason = f"Section 80EEA Ineligible: Loan sanction date ({sanction_date}) is outside the statutory window (01-Apr-2019 to 31-Mar-2022)."
            allowed_deduction = 0.0
        elif not cond_stamp_value:
            reason = f"Section 80EEA Ineligible: Property stamp duty value (INR {stamp_val:,.2f}) exceeds statutory limit of INR 45,00,000."
            allowed_deduction = 0.0
        elif not cond_first_buyer:
            reason = "Section 80EEA Ineligible: Assessee is not a First-Time Home Buyer on the date of loan sanction."
            allowed_deduction = 0.0
        elif not cond_no_80ee:
            reason = "Section 80EEA Ineligible: Assessee has already claimed deduction under Section 80EE."
        elif claimed_amt <= 0.0:
            reason = "No Section 80EEA deduction allowable: Declared interest amount is zero."
            allowed_deduction = 0.0
        else:
            allowed_deduction = min(claimed_amt, max_ceiling)
            if claimed_amt > max_ceiling:
                reason = f"Assessee satisfies all statutory criteria under Section 80EEA. Declared interest of INR {claimed_amt:,.2f} capped at statutory ceiling of INR {max_ceiling:,.2f}."
            else:
                reason = f"Assessee satisfies all statutory criteria under Section 80EEA. Full declared interest of INR {claimed_amt:,.2f} allowed."

        remarks = (
            f"Section 80EEA Status: {'ELIGIBLE' if is_eligible else 'INELIGIBLE'}. {reason}"
        )

        sanction_date_str = sanction_date.strftime('%d-%b-%Y') if hasattr(sanction_date, 'strftime') and sanction_date else (str(sanction_date) if sanction_date else 'N/A')

        # Structured SECTION 80EEA STATUTORY TRACE Logging
        trace_log = f"""
=========================================================
SECTION 80EEA STATUTORY TRACE (First-Time Home Buyer)
=========================================================

Employee                : {emp_name}
Employee ID             : {emp_id}
Financial Year          : {fy_name}
Declaration ID          : {decl_id}

---------------------------------------------------------
DECLARATION & LOAN INPUTS
---------------------------------------------------------

Tax Regime              : {regime.upper()}
Declared Interest       : INR {claimed_amt:,.2f}
Loan Sanction Date      : {sanction_date_str}
Property Stamp Value    : INR {stamp_val:,.2f}
First-Time Home Buyer   : {"YES" if is_first_buyer else "NO"}
Section 80EE Claimed    : {"YES" if claimed_80ee else "NO"}
Lending Institution     : {lending_inst}
Loan Account Number     : {acct_num}

---------------------------------------------------------
STATUTORY CONDITION EVALUATIONS
---------------------------------------------------------

1. Tax Regime Permitted (Old Regime Only)      : {"PASS" if cond_regime else "FAIL"}
2. Loan Sanction Window (01-Apr-19 - 31-Mar-22): {"PASS (" + sanction_date_str + ")" if cond_date_window else "FAIL (" + sanction_date_str + ")"}
3. Property Stamp Value (<= INR 45,00,000)    : {"PASS (INR " + f"{stamp_val:,.2f}" + ")" if cond_stamp_value else "FAIL (INR " + f"{stamp_val:,.2f}" + ")"}
4. First-Time Home Buyer Requirement          : {"PASS" if cond_first_buyer else "FAIL"}
5. Section 80EE Exclusivity Requirement       : {"PASS" if cond_no_80ee else "FAIL"}

---------------------------------------------------------
STATUTORY DEDUCTION CALCULATION
---------------------------------------------------------

Overall Eligibility     : {"ELIGIBLE" if is_eligible else "INELIGIBLE"}
Declared Amount         : INR {claimed_amt:,.2f}
Statutory Ceiling Cap   : INR {max_ceiling:,.2f}

Allowed Exemption

= INR {allowed_deduction:,.2f}

Reason

{reason}

=========================================================
FINAL SECTION 80EEA DEDUCTION
=========================================================

Allowed Deduction

INR {allowed_deduction:,.2f}

=========================================================
"""
        _logger.warning(trace_log)

        return Section80EEAValidationResult(
            is_eligible=is_eligible,
            remarks=remarks,
            max_statutory_ceiling=max_ceiling,
            allowed_deduction=allowed_deduction
        )
