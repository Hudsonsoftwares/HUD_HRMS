# -*- coding: utf-8 -*-
import logging
from ..base import BaseStatutoryService
from .employee_tax_declaration_validation_service import EmployeeTaxDeclarationValidationService

_logger = logging.getLogger(__name__)


class Chapter6aDeductionResult:
    """
    Data Transfer Object (DTO) holding Chapter VI-A approved deductions breakdown.
    """
    def __init__(self, section_80c=0.0, section_80ccd1b=0.0, section_80d=0.0,
                 section_80dd=0.0, section_80tta_80ttb=0.0, section_80eea=0.0,
                 other_80_deductions=0.0, total_chapter_6a=0.0):
        self.section_80c = section_80c
        self.section_80ccd1b = section_80ccd1b
        self.section_80d = section_80d
        self.section_80dd = section_80dd
        self.section_80tta_80ttb = section_80tta_80ttb
        self.section_80eea = section_80eea
        self.other_80_deductions = other_80_deductions
        self.total_chapter_6a = total_chapter_6a


class Chapter6aDeductionService(BaseStatutoryService):
    """
    Phase 5 Service: Chapter VI-A Deduction Service.
    Calculates approved Chapter VI-A deductions for the employee:
    Section 80C, Section 80CCD(1B), Section 80D, Section 80DD, Section 80TTA / 80TTB.
    Strictly enforces regime restrictions (returns 0.0 for all Chapter VI-A under New Tax Regime).
    """

    def calculate_chapter_6a_deductions(self, employee, financial_year, regime_code, eval_date=None):
        """
        Calculates approved Chapter VI-A deductions.

        :param employee: hr.employee record
        :param financial_year: tds.financial.year record
        :param regime_code: str ('old' or 'new')
        :param eval_date: Date (optional)
        :return: Chapter6aDeductionResult
        """
        regime_code = (regime_code or 'new').lower()

        # Under New Tax Regime (Section 115BAC), Chapter VI-A deductions are strictly prohibited
        if regime_code == 'new':
            return Chapter6aDeductionResult()

        decl = self.env['tds.employee.declaration'].search([
            ('employee_id', '=', employee.id),
            ('financial_year_id', '=', financial_year.id)
        ], limit=1)

        reg_rec = self.env['tds.employee.tax.regime'].search([
            ('employee_id', '=', employee.id),
            ('financial_year_id', '=', financial_year.id)
        ], limit=1)

        _logger.info(
            "\n======================================\n"
            "REGIME TRACE\n"
            "======================================\n"
            "Employee                     : %s (ID: %s)\n"
            "Financial Year               : %s (ID: %s)\n"
            "Employee Tax Regime Record ID: %s\n"
            "Selected Regime in Database  : %s\n"
            "Resolved Regime Code         : %s\n"
            "Resolved Regime Name         : %s\n"
            "======================================",
            employee.name if employee else 'N/A', employee.id if employee else 'N/A',
            financial_year.name if financial_year else 'N/A', financial_year.id if financial_year else 'N/A',
            reg_rec.id if reg_rec else 'None',
            reg_rec.regime_id.code if (reg_rec and reg_rec.regime_id) else 'None',
            regime_code.upper(),
            reg_rec.regime_id.name if (reg_rec and reg_rec.regime_id) else 'N/A'
        )

        if not decl:
            return Chapter6aDeductionResult()

        val_svc = EmployeeTaxDeclarationValidationService(self.env)
        val_svc.validate_declaration(decl, regime_code=regime_code, eval_date=eval_date)

        from .tds_parameter_service import TdsParameterService
        tds_param_svc = TdsParameterService(self.env)
        max_80c = tds_param_svc.get_80c_limit(eval_date=eval_date) or 150000.0
        max_80ccd1b = tds_param_svc.get_80ccd1b_limit(eval_date=eval_date) or 50000.0

        raw_80c = 0.0
        raw_80ccd1b = 0.0
        section_80d = 0.0
        section_80dd = 0.0
        section_80tta_80ttb = 0.0
        section_80eea = 0.0
        other_80 = 0.0

        running_total = 0.0

        for line in decl.declaration_line_ids:
            cat = line.category
            amt = line.usable_amount
            is_permitted = line.is_regime_permitted
            is_act = getattr(line, 'active', True)

            reason = "Included in deduction calculation"
            selected_amt = 0.0

            if not is_permitted:
                reason = "Skipped: Category prohibited under active tax regime (is_regime_permitted = False)"
            elif not is_act:
                reason = "Skipped: Declaration line item inactive (active = False)"
            else:
                selected_amt = amt
                if cat == '80c':
                    raw_80c += amt
                elif cat == '80ccd1b':
                    raw_80ccd1b += amt
                elif cat in ('80d_self', '80d_parents', '80d_preventive'):
                    section_80d += amt
                elif cat == '80dd':
                    section_80dd += amt
                elif cat in ('80tta', '80ttb'):
                    section_80tta_80ttb += amt
                elif cat == '80eea':
                    section_80eea += amt
                elif cat in ('80e', '80g', '80gg'):
                    other_80 += amt
                running_total += selected_amt

            _logger.info(
                "--------------------------------------\n"
                "Category               : %s\n"
                "Description            : %s\n"
                "Declared Amount        : ₹%s\n"
                "Approved Amount        : ₹%s\n"
                "Usable Amount          : ₹%s\n"
                "is_regime_permitted    : %s\n"
                "is_active              : %s\n"
                "Selected Amount        : ₹%s\n"
                "Reason Included/Skipped: %s\n"
                "Running Total Chapter VI-A: ₹%s",
                cat, line.description, line.declared_amount, line.approved_amount,
                line.usable_amount, is_permitted, is_act, selected_amt, reason, running_total
            )

        section_80c = min(raw_80c, max_80c)
        section_80ccd1b = min(raw_80ccd1b, max_80ccd1b)

        total_chapter_6a = (
            section_80c + section_80ccd1b + section_80d +
            section_80dd + section_80tta_80ttb + section_80eea + other_80
        )

        _logger.info(
            "======================================\n"
            "Final Chapter VI-A Total : ₹%s\n"
            "======================================",
            total_chapter_6a
        )

        return Chapter6aDeductionResult(
            section_80c=section_80c,
            section_80ccd1b=section_80ccd1b,
            section_80d=section_80d,
            section_80dd=section_80dd,
            section_80tta_80ttb=section_80tta_80ttb,
            section_80eea=section_80eea,
            other_80_deductions=other_80,
            total_chapter_6a=total_chapter_6a
        )
