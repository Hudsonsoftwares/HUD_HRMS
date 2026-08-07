# -*- coding: utf-8 -*-
import logging
from odoo import fields
from ..base import BaseStatutoryService
from .tds_parameter_service import TdsParameterService
from ...models.tds_employee_declaration import DECLARATION_BUSINESS_REGISTRY

_logger = logging.getLogger(__name__)


class EligibilityResult:
    """
    Data Transfer Object (DTO) holding the dynamic result of a statutory eligibility rule evaluation.
    """
    def __init__(self, category, source_amount, statutory_limit, eligible_deduction, excess_amount, rule_applied, calculation_phase, parameter_code_selected='N/A', parameter_value=0.0):
        self.category = category
        self.source_amount = source_amount
        self.statutory_limit = statutory_limit
        self.eligible_deduction = eligible_deduction
        self.excess_amount = excess_amount
        self.rule_applied = rule_applied
        self.calculation_phase = calculation_phase
        self.parameter_code_selected = parameter_code_selected
        self.parameter_value = parameter_value


class EligibilityRuleEngineService(BaseStatutoryService):
    """
    Centralized Strategy-Driven Statutory Eligibility Rule Engine Service.
    Dynamically computes Eligible Deductions and Excess Amounts directly from declaration line context and DECLARATION_BUSINESS_REGISTRY metadata.
    
    Phases:
    - Planning Phase (April–November / draft, declared, submitted): Source = Declared Amount
    - Final Adjustment Phase (December–March / proof_verified, approved): Source = Approved Amount (if available, else Declared)
    """

    def evaluate_eligibility(self, declaration_line_or_category, eval_date=None, **kwargs):
        """
        Master context-driven method to evaluate statutory deduction eligibility using Strategy Pattern dispatch.

        :param declaration_line_or_category: tds.employee.declaration.line record OR category string
        :param eval_date: Date (optional)
        :param kwargs: Fallback parameters if category string passed
        :return: EligibilityResult
        """
        eval_date = eval_date or fields.Date.today()

        if hasattr(declaration_line_or_category, 'category'):
            line = declaration_line_or_category
            line_id = line.id if line.id else 'New'
            category = line.category
            declared_val = float(line.declared_amount or 0.0)
            approved_val = float(line.approved_amount or 0.0)
            is_senior = bool(getattr(line, 'is_senior_citizen', False))
            is_severe = bool(getattr(line, 'is_severe_disability', False))
            regime_code = (getattr(line, 'regime_code', 'old') or 'old').lower()
            decl = getattr(line, 'declaration_id', False)
            declaration_state = decl.state if decl else 'draft'
        else:
            line_id = kwargs.get('line_id', 'N/A')
            category = str(declaration_line_or_category or '')
            declared_val = float(kwargs.get('declared_amount', 0.0) or 0.0)
            approved_val = float(kwargs.get('approved_amount', 0.0) or 0.0)
            is_senior = bool(kwargs.get('is_senior_citizen', False))
            is_severe = bool(kwargs.get('is_severe_disability', False))
            regime_code = (kwargs.get('regime_code', 'old') or 'old').lower()
            declaration_state = kwargs.get('declaration_state', 'draft')

        # 1. Determine Calculation Phase & Active Source Amount
        if declaration_state in ('proof_verified', 'approved'):
            phase = "Final Adjustment Phase"
            source_amount = approved_val if approved_val > 0.0 else declared_val
        else:
            phase = "Planning Phase"
            source_amount = declared_val

        # 2. Look up Strategy & Regime Metadata from DECLARATION_BUSINESS_REGISTRY
        registry_item = next((item for item in DECLARATION_BUSINESS_REGISTRY if item['category'] == category), None)
        allowed_regimes = registry_item.get('allowed_regimes', ['old']) if registry_item else ['old']

        # 3. Resolve Statutory Parameter Code & Limit via TdsParameterService
        tds_param_svc = TdsParameterService(self.env)
        limit = float('inf')
        param_code = registry_item.get('parameter_code', 'NONE') if registry_item else 'NONE'

        if category == '80c':
            param_code = 'HDS_IN_TDS_80C_MAX_LIMIT'
            limit = tds_param_svc.get_80c_limit(eval_date=eval_date) or 150000.0

        elif category == '80ccd1b':
            param_code = 'HDS_IN_TDS_80CCD1B_MAX_LIMIT'
            limit = tds_param_svc.get_80ccd1b_limit(eval_date=eval_date) or 50000.0

        elif category == '24b':
            param_code = 'HDS_IN_TDS_24B_HOME_LOAN_INTEREST_LIMIT'
            limit = tds_param_svc.get_home_loan_interest_limit(eval_date=eval_date) or 200000.0

        elif category == '80d_self':
            if is_senior:
                param_code = 'HDS_IN_TDS_80D_SELF_SENIOR_MAX_LIMIT'
                limit = tds_param_svc.get_80d_limit(is_senior=True, is_parents=False, eval_date=eval_date) or 50000.0
            else:
                param_code = 'HDS_IN_TDS_80D_SELF_MAX_LIMIT'
                limit = tds_param_svc.get_80d_limit(is_senior=False, is_parents=False, eval_date=eval_date) or 25000.0

        elif category == '80d_parents':
            if is_senior:
                param_code = 'HDS_IN_TDS_80D_PARENTS_SENIOR_MAX_LIMIT'
                limit = tds_param_svc.get_80d_limit(is_senior=True, is_parents=True, eval_date=eval_date) or 50000.0
            else:
                param_code = 'HDS_IN_TDS_80D_PARENTS_MAX_LIMIT'
                limit = tds_param_svc.get_80d_limit(is_senior=False, is_parents=True, eval_date=eval_date) or 25000.0

        elif category == '80d_preventive':
            preventive_sublimit = tds_param_svc.get_parameter('80D_PREVENTIVE_CHECKUP_LIMIT', eval_date=eval_date) or 5000.0
            overall_self_ceiling = tds_param_svc.get_80d_limit(is_senior=is_senior, is_parents=False, eval_date=eval_date) or 25000.0
            declared_self = 0.0
            if hasattr(declaration_line_or_category, 'declaration_id') and declaration_line_or_category.declaration_id:
                self_lines = declaration_line_or_category.declaration_id.declaration_line_ids.filtered(lambda l: l.category == '80d_self')
                declared_self = sum(l.declared_amount for l in self_lines)
            elif 'declared_self_insurance' in kwargs:
                declared_self = float(kwargs['declared_self_insurance'] or 0.0)

            remaining_self_cap = max(0.0, overall_self_ceiling - declared_self)
            param_code = 'HDS_IN_TDS_80D_PREVENTIVE_CHECKUP_LIMIT'
            limit = min(preventive_sublimit, remaining_self_cap)

        elif category == '80tta':
            param_code = 'HDS_IN_TDS_80TTA_MAX_LIMIT'
            limit = tds_param_svc.get_parameter('80TTA_MAX_LIMIT', eval_date=eval_date) or 10000.0

        elif category == '80ttb':
            param_code = 'HDS_IN_TDS_80TTB_MAX_LIMIT'
            limit = tds_param_svc.get_parameter('80TTB_MAX_LIMIT', eval_date=eval_date) or 50000.0

        elif category == '80dd':
            if is_severe:
                param_code = 'HDS_IN_TDS_80DD_SEVERE_LIMIT'
                limit = tds_param_svc.get_parameter('80DD_SEVERE_LIMIT', eval_date=eval_date) or 125000.0
            else:
                param_code = 'HDS_IN_TDS_80DD_NORMAL_LIMIT'
                limit = tds_param_svc.get_parameter('80DD_NORMAL_LIMIT', eval_date=eval_date) or 75000.0

        elif category == '80eea':
            param_code = 'HDS_IN_TDS_80EEA_MAX_LIMIT'
            limit = tds_param_svc.get_parameter('80EEA_MAX_LIMIT', eval_date=eval_date) or 150000.0

        elif category == 'leave_encashment':
            param_code = 'HDS_IN_TDS_LEAVE_ENCASHMENT_EXEMPTION_CEILING'
            limit = tds_param_svc.get_leave_encashment_ceiling(eval_date=eval_date) or 2500000.0

        elif category == 'vrs':
            param_code = 'HDS_IN_TDS_VRS_EXEMPTION_CEILING'
            limit = tds_param_svc.get_parameter('VRS_EXEMPTION_CEILING', eval_date=eval_date) or 500000.0

        # 4. Calculate Eligible Deduction & Excess Amount with Regime Validation
        if regime_code not in allowed_regimes:
            eligible_deduction = 0.0
            excess_amount = source_amount
            rule_applied = f"Section {category.upper()} prohibited under {regime_code.upper()} Tax Regime (Allowed: {allowed_regimes})."
        else:
            if limit < float('inf'):
                eligible_deduction = min(source_amount, limit)
                excess_amount = max(0.0, source_amount - eligible_deduction)
                rule_applied = f"Statutory ceiling of ₹{limit:,.2f} ({param_code}) applied under {regime_code.upper()} Regime."
            else:
                eligible_deduction = source_amount
                excess_amount = 0.0
                rule_applied = f"100% Eligible under {regime_code.upper()} Regime (No statutory cap)."

        # 5. Log Structured ELIGIBILITY TRACE
        _logger.info(
            "\n========================================\n"
            "ELIGIBILITY TRACE\n"
            "========================================\n"
            "Line ID                : %s\n"
            "Category               : %s\n"
            "Declared Amount        : ₹%s\n"
            "Approved Amount        : ₹%s\n"
            "Declaration State      : %s\n"
            "Regime                 : %s\n"
            "is_senior_citizen      : %s\n"
            "Parameter Code Selected: %s\n"
            "Parameter Value        : %s\n"
            "Eligible Amount        : ₹%s\n"
            "Excess Amount          : ₹%s\n"
            "Rule Applied           : %s\n"
            "========================================",
            line_id, category.upper(), f"{declared_val:,.2f}", f"{approved_val:,.2f}",
            declaration_state, regime_code.upper(), is_senior,
            param_code, f"₹{limit:,.2f}" if limit < float('inf') else "Unlimited",
            f"{eligible_deduction:,.2f}", f"{excess_amount:,.2f}", rule_applied
        )

        return EligibilityResult(
            category=category,
            source_amount=source_amount,
            statutory_limit=limit if limit < float('inf') else 0.0,
            eligible_deduction=eligible_deduction,
            excess_amount=excess_amount,
            rule_applied=rule_applied,
            calculation_phase=phase,
            parameter_code_selected=param_code,
            parameter_value=limit if limit < float('inf') else 0.0
        )
