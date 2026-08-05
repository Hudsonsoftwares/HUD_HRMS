# -*- coding: utf-8 -*-
import logging
from ..base import BaseStatutoryService
from .tds_parameter_service import TdsParameterService
from .section_80eea_eligibility_service import Section80EEAEligibilityService

_logger = logging.getLogger(__name__)


class HomeLoanDeductionResult:
    """
    Data Transfer Object (DTO) holding housing loan deduction calculation details.
    """
    def __init__(self, section_24b_self_interest=0.0, section_80eea_interest=0.0, total_home_loan_deduction=0.0):
        self.section_24b_self_interest = section_24b_self_interest
        self.section_80eea_interest = section_80eea_interest
        self.total_home_loan_deduction = total_home_loan_deduction


class HomeLoanDeductionService(BaseStatutoryService):
    """
    Phase 5 Service: Home Loan Deduction Service.
    Evaluates housing loan deductions:
    1. Section 24(b) Self-Occupied Home Loan Interest (capped at ₹2,00,000 via TdsParameterService).
    2. Section 80EEA First-Time Home Buyer additional interest (capped at ₹1,50,000 after invoking Section80EEAEligibilityService).
    Strictly returns 0.0 under New Tax Regime (Section 115BAC prohibits 24(b) self-occupied and 80EEA).
    """

    def calculate_home_loan_deductions(self, employee, financial_year, regime_code, eval_date=None):
        """
        Calculates housing loan deductions.

        :param employee: hr.employee record
        :param financial_year: tds.financial.year record
        :param regime_code: str ('old' or 'new')
        :param eval_date: Date (optional)
        :return: HomeLoanDeductionResult
        """
        regime_code = (regime_code or 'new').lower()

        if regime_code == 'new':
            return HomeLoanDeductionResult()

        tds_param_svc = TdsParameterService(self.env)
        max_24b_limit = tds_param_svc.get_home_loan_interest_limit(eval_date=eval_date)

        # 1. Section 24(b) Self-Occupied Interest from declaration
        decl = self.env['tds.employee.declaration'].search([
            ('employee_id', '=', employee.id),
            ('financial_year_id', '=', financial_year.id)
        ], limit=1)

        sec_24b_amt = 0.0
        if decl:
            for line in decl.declaration_line_ids:
                if line.category == '24b' and line.is_regime_permitted:
                    sec_24b_amt += line.declared_amount or 0.0

        sec_24b_approved = min(sec_24b_amt, max_24b_limit)

        # 2. Section 80EEA Eligibility Service Invocation
        sec_80eea_approved = 0.0
        home_loans = self.env['tds.employee.home.loan'].search([
            ('employee_id', '=', employee.id),
            ('financial_year_id', '=', financial_year.id)
        ], limit=1)

        if home_loans:
            eea_svc = Section80EEAEligibilityService(self.env)
            eea_res = eea_svc.validate_eligibility(home_loans, eval_date=eval_date)
            if eea_res.is_eligible:
                sec_80eea_approved = eea_res.allowed_deduction

        total_home_loan = sec_24b_approved + sec_80eea_approved

        return HomeLoanDeductionResult(
            section_24b_self_interest=sec_24b_approved,
            section_80eea_interest=sec_80eea_approved,
            total_home_loan_deduction=total_home_loan
        )
