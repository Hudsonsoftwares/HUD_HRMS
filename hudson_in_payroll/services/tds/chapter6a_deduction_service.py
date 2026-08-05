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

        if not decl:
            return Chapter6aDeductionResult()

        val_svc = EmployeeTaxDeclarationValidationService(self.env)
        val_svc.validate_declaration(decl, eval_date=eval_date)

        section_80c = 0.0
        section_80ccd1b = 0.0
        section_80d = 0.0
        section_80dd = 0.0
        section_80tta_80ttb = 0.0
        section_80eea = 0.0
        other_80 = 0.0

        for line in decl.declaration_line_ids:
            if not line.is_regime_permitted:
                continue

            cat = line.category
            amt = line.approved_amount or 0.0

            if cat == '80c':
                section_80c += amt
            elif cat == '80ccd1b':
                section_80ccd1b += amt
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

        total_chapter_6a = (
            section_80c + section_80ccd1b + section_80d +
            section_80dd + section_80tta_80ttb + section_80eea + other_80
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
