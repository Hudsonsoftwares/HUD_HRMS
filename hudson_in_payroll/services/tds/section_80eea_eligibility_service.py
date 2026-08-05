# -*- coding: utf-8 -*-
import logging
from datetime import datetime
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
    Enforces statutory eligibility rules under Section 80EEA of the Income Tax Act
    BEFORE retrieving the statutory monetary ceiling from TdsParameterService.

    Statutory Eligibility Criteria (Section 80EEA):
    1. Housing loan sanctioned between 01-Apr-2019 and 31-Mar-2022.
    2. Stamp duty value of residential house property <= ₹45,00,000 (INR 45 Lakhs).
    3. Employee is a First-Time Home Buyer (does not own any residential property on loan sanction date).
    """

    # Statutory date boundaries
    SECTION_80EEA_START_DATE = fields.Date.from_string('2019-04-01')
    SECTION_80EEA_END_DATE = fields.Date.from_string('2022-03-31')
    MAX_STAMP_DUTY_VALUE = 4500000.0  # ₹45 Lakhs

    def validate_eligibility(self, home_loan_record_or_dict, eval_date=None):
        """
        Validates statutory Section 80EEA eligibility for a home loan declaration record or data dictionary.

        :param home_loan_record_or_dict: tds.employee.home.loan recordset or dict containing:
               - loan_sanction_date (Date/str)
               - property_stamp_value (float)
               - is_first_time_home_buyer (bool)
               - claimed_interest_amount (float)
        :param eval_date: Date (optional)
        :return: Section80EEAValidationResult
        """
        tds_param_svc = TdsParameterService(self.env)
        if not eval_date:
            eval_date = fields.Date.today()

        # Extract values cleanly whether passed ORM recordset or raw dict
        if hasattr(home_loan_record_or_dict, 'loan_sanction_date'):
            sanction_date = home_loan_record_or_dict.loan_sanction_date
            stamp_val = home_loan_record_or_dict.property_stamp_value or 0.0
            is_first_buyer = bool(home_loan_record_or_dict.is_first_time_home_buyer)
            claimed_amt = home_loan_record_or_dict.claimed_interest_amount or 0.0
        else:
            d = home_loan_record_or_dict or {}
            sanction_date = d.get('loan_sanction_date')
            stamp_val = float(d.get('property_stamp_value', 0.0))
            is_first_buyer = bool(d.get('is_first_time_home_buyer', True))
            claimed_amt = float(d.get('claimed_interest_amount', 0.0))

        if isinstance(sanction_date, str):
            sanction_date = fields.Date.from_string(sanction_date)

        # 1. Validate Loan Sanction Date presence
        if not sanction_date:
            return Section80EEAValidationResult(
                is_eligible=False,
                remarks="Section 80EEA Ineligible: Loan Sanction Date is missing or invalid.",
                max_statutory_ceiling=0.0,
                allowed_deduction=0.0
            )

        # 2. Condition 1: Sanction Date between 01-Apr-2019 and 31-Mar-2022
        if sanction_date < self.SECTION_80EEA_START_DATE:
            return Section80EEAValidationResult(
                is_eligible=False,
                remarks=f"Section 80EEA Ineligible: Loan sanction date ({sanction_date}) is prior to 01-Apr-2019. Section 80EEA applies only to loans sanctioned between 01-Apr-2019 and 31-Mar-2022.",
                max_statutory_ceiling=0.0,
                allowed_deduction=0.0
            )

        if sanction_date > self.SECTION_80EEA_END_DATE:
            return Section80EEAValidationResult(
                is_eligible=False,
                remarks=f"Section 80EEA Ineligible: Loan sanction date ({sanction_date}) is after 31-Mar-2022. Section 80EEA statutory scheme expired on 31-Mar-2022.",
                max_statutory_ceiling=0.0,
                allowed_deduction=0.0
            )

        # 3. Condition 2: Stamp duty value <= ₹45 Lakhs
        if stamp_val > self.MAX_STAMP_DUTY_VALUE:
            return Section80EEAValidationResult(
                is_eligible=False,
                remarks=f"Section 80EEA Ineligible: Property stamp duty value (₹{stamp_val:,.2f}) exceeds statutory ceiling limit of ₹45,00,000 for Section 80EEA.",
                max_statutory_ceiling=0.0,
                allowed_deduction=0.0
            )

        # 4. Condition 3: First-time home buyer
        if not is_first_buyer:
            return Section80EEAValidationResult(
                is_eligible=False,
                remarks="Section 80EEA Ineligible: Assessee is not a First-Time Home Buyer on the date of loan sanction.",
                max_statutory_ceiling=0.0,
                allowed_deduction=0.0
            )

        # 5. ALL CONDITIONS PASSED -> Resolve statutory ceiling from hr.rule.parameter
        max_ceiling = tds_param_svc.get_parameter('80EEA_MAX_LIMIT', eval_date=eval_date)
        allowed_deduction = min(claimed_amt, max_ceiling) if claimed_amt > 0 else 0.0

        remarks = (
            f"Section 80EEA Eligible: Satisfies sanction window (01-Apr-2019 to 31-Mar-2022), stamp value (₹{stamp_val:,.0f} <= ₹45L), and First-Time Home Buyer criteria. "
            f"Claimed Interest: ₹{claimed_amt:,.2f}, Statutory Limit: ₹{max_ceiling:,.2f}, Approved Section 80EEA Deduction: ₹{allowed_deduction:,.2f}."
        )

        return Section80EEAValidationResult(
            is_eligible=True,
            remarks=remarks,
            max_statutory_ceiling=max_ceiling,
            allowed_deduction=allowed_deduction
        )
