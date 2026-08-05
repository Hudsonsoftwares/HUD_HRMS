# -*- coding: utf-8 -*-
import logging
from dateutil.relativedelta import relativedelta
from odoo import fields
from ..base import BaseStatutoryService
from .tds_parameter_service import TdsParameterService
from .section_80eea_eligibility_service import Section80EEAEligibilityService

_logger = logging.getLogger(__name__)


class EmployeeDeclarationValidationReport:
    """
    Data Transfer Object representing the result of an Employee Tax Declaration statutory audit.
    """
    def __init__(self, declaration_id, regime_code, is_compliant, total_declared, total_approved, line_results=None, error_messages=None):
        self.declaration_id = declaration_id
        self.regime_code = regime_code
        self.is_compliant = is_compliant
        self.total_declared = total_declared
        self.total_approved = total_approved
        self.line_results = line_results or []
        self.error_messages = error_messages or []


class EmployeeTaxDeclarationValidationService(BaseStatutoryService):
    """
    Centralized Validation Service for Employee Tax Declarations & Investment Proofs.
    Enforces regime compatibility (New vs Old) and resolves statutory deduction ceilings
    exclusively through TdsParameterService.
    """

    # Deduction categories strictly prohibited under New Tax Regime (Section 115BAC)
    NEW_REGIME_DISALLOWED_CATEGORIES = {
        '80c', 'nps_employee', '80ccd1b', '80d_self', '80d_parents', '80d_preventive',
        '80tta', '80ttb', '80dd', '24b', '80eea', 'hra', 'children_edu',
        'hostel', 'lta'
    }

    # Enterprise Mutually Exclusive Category Sets (Categories within each set cannot coexist in the same Financial Year)
    MUTUALLY_EXCLUSIVE_CATEGORY_SETS = [
        {
            'categories': {'80tta', '80ttb'},
            'rule_name': 'Section 80TTA / 80TTB Mutual Exclusivity',
            'conflict_remarks': "Statutory Conflict: Section 80TTA (Non-Senior Savings Interest) and Section 80TTB (Senior Citizen Deposit Interest) are mutually exclusive under Section 80TTA(2). An employee cannot claim both in the same Financial Year."
        }
    ]


    def _is_employee_senior_citizen_in_fy(self, employee, financial_year, eval_date=None):
        """
        Determines whether an employee attains age 60 at ANY time during the Financial Year
        under Indian Income Tax statutory rules (CBDT Circular No. 19/2015 & Circular No. 28/2018).

        :param employee: hr.employee record
        :param financial_year: tds.financial.year record
        :param eval_date: Date (optional fallback)
        :return: Boolean (True if employee turns 60 by March 31 of the Financial Year)
        """
        if not employee or not employee.birthday:
            return False

        if financial_year and financial_year.end_date:
            fy_end = financial_year.end_date
        elif eval_date:
            fy_year = eval_date.year if eval_date.month >= 4 else eval_date.year - 1
            fy_end = fields.Date.from_string(f"{fy_year + 1}-03-31")
        else:
            today = fields.Date.today()
            fy_year = today.year if today.month >= 4 else today.year - 1
            fy_end = fields.Date.from_string(f"{fy_year + 1}-03-31")

        # Calendar-aware exact age determination at Financial Year end
        age_at_fy_end = relativedelta(fy_end, employee.birthday).years
        return age_at_fy_end >= 60

    def validate_declaration(self, declaration_record, eval_date=None):

        """
        Validates an employee declaration header and all underlying declaration line items.

        :param declaration_record: tds.employee.declaration recordset
        :param eval_date: Date (optional)
        :return: EmployeeDeclarationValidationReport
        """
        declaration_record.ensure_one()
        tds_param_svc = TdsParameterService(self.env)
        eea_svc = Section80EEAEligibilityService(self.env)

        eval_date = eval_date or fields.Date.today()
        regime_code = (declaration_record.regime_code or 'new').lower()
        max_80c_ceiling = tds_param_svc.get_80c_limit(eval_date=eval_date)

        is_compliant = True
        line_results = []
        error_messages = []
        accumulated_80c = 0.0
        declared_categories = {l.category for l in declaration_record.declaration_line_ids}

        for line in declaration_record.declaration_line_ids:

            cat = line.category
            declared_val = line.declared_amount or 0.0

            # -----------------------------------------------------------------
            # 1. NEW REGIME PROHIBITED CATEGORY ENFORCEMENT
            # -----------------------------------------------------------------
            if regime_code == 'new' and cat in self.NEW_REGIME_DISALLOWED_CATEGORIES:
                line.write({
                    'is_regime_permitted': False,
                    'validation_status': 'ineligible_regime',
                    'approved_amount': 0.0,
                    'validation_remarks': f"Category '{cat}' (e.g. Section 80C/80CCD(1)/80D/HRA) is strictly prohibited under the New Tax Regime (Section 115BAC).",
                })
                is_compliant = False
                error_messages.append(f"Line '{line.description}': {line.section_code} not permitted under New Regime.")
                line_results.append({'line_id': line.id, 'category': cat, 'approved_amount': 0.0, 'status': 'ineligible_regime'})
                continue

            # -----------------------------------------------------------------
            # 2. OLD REGIME & SHARED CATEGORY STATUTORY VALIDATION
            # -----------------------------------------------------------------
            line.is_regime_permitted = True
            approved_val = declared_val
            val_status = 'valid'
            val_remarks = "Statutory deduction verified and valid."

            if cat in ('80c', 'nps_employee'):
                # Group ceiling enforcement across multiple 80C / 80CCD(1) lines
                remaining_80c_cap = max(0.0, max_80c_ceiling - accumulated_80c)
                if declared_val > remaining_80c_cap:
                    approved_val = remaining_80c_cap
                    val_status = 'exceeds_limit'
                    val_remarks = f"Section 80C / 80CCD(1) cumulative claim capped at statutory limit of ₹{max_80c_ceiling:,.2f}."
                accumulated_80c += approved_val

            elif cat == '80ccd1b':
                ceiling = tds_param_svc.get_80ccd1b_limit(eval_date=eval_date)
                if declared_val > ceiling:
                    approved_val = ceiling
                    val_status = 'exceeds_limit'
                    val_remarks = f"Section 80CCD(1B) additional NPS claim capped at statutory limit of ₹{ceiling:,.2f}."

            elif cat == '80d_self':
                emp_is_senior = line.is_senior_citizen or self._is_employee_senior_citizen_in_fy(
                    declaration_record.employee_id,
                    declaration_record.financial_year_id,
                    eval_date=eval_date
                )
                ceiling = tds_param_svc.get_80d_limit(is_senior=emp_is_senior, is_parents=False, eval_date=eval_date)
                if declared_val > ceiling:
                    approved_val = ceiling
                    val_status = 'exceeds_limit'
                    val_remarks = f"Section 80D (Self {'Senior Citizen' if emp_is_senior else 'Non-Senior'}) claim capped at statutory limit of ₹{ceiling:,.2f}."


            elif cat == '80d_parents':
                parent_is_senior = line.is_senior_citizen
                ceiling = tds_param_svc.get_80d_limit(is_senior=parent_is_senior, is_parents=True, eval_date=eval_date)
                if declared_val > ceiling:
                    approved_val = ceiling
                    val_status = 'exceeds_limit'
                    val_remarks = f"Section 80D (Parents {'Senior Citizen' if parent_is_senior else 'Non-Senior'}) claim capped at statutory limit of ₹{ceiling:,.2f}."


            elif cat == '80d_preventive':
                ceiling = tds_param_svc.get_parameter('80D_PREVENTIVE_CHECKUP_LIMIT', eval_date=eval_date)
                if declared_val > ceiling:
                    approved_val = ceiling
                    val_status = 'exceeds_limit'
                    val_remarks = f"Section 80D Preventive Checkup sub-limit capped at ₹{ceiling:,.2f}."

            elif cat == '80tta':
                is_emp_senior = self._is_employee_senior_citizen_in_fy(
                    declaration_record.employee_id,
                    declaration_record.financial_year_id,
                    eval_date=eval_date
                )
                if is_emp_senior:
                    approved_val = 0.0
                    val_status = 'ineligible_regime'
                    val_remarks = "Ineligible under Section 80TTA(2): Employee is a Senior Citizen (Age 60+). Senior Citizens are prohibited from claiming Section 80TTA and must claim Section 80TTB instead."
                    is_compliant = False
                elif '80ttb' in declared_categories:
                    approved_val = 0.0
                    val_status = 'ineligible_regime'
                    val_remarks = "Statutory Conflict: Section 80TTA and Section 80TTB are mutually exclusive under Section 80TTA(2). Simultaneous claims in the same Financial Year are prohibited."
                    is_compliant = False
                else:
                    ceiling = tds_param_svc.get_parameter('80TTA_MAX_LIMIT', eval_date=eval_date)
                    if declared_val > ceiling:
                        approved_val = ceiling
                        val_status = 'exceeds_limit'
                        val_remarks = f"Section 80TTA Savings Interest claim capped at statutory limit of ₹{ceiling:,.2f}."

            elif cat == '80ttb':
                is_emp_senior = self._is_employee_senior_citizen_in_fy(
                    declaration_record.employee_id,
                    declaration_record.financial_year_id,
                    eval_date=eval_date
                )
                if not is_emp_senior:
                    approved_val = 0.0
                    val_status = 'ineligible_regime'
                    val_remarks = "Ineligible under Section 80TTB: Section 80TTB is restricted strictly to Senior Citizens (Age 60+). Non-Senior employees must claim Section 80TTA instead."
                    is_compliant = False
                elif '80tta' in declared_categories and is_emp_senior:
                    # If both exist and employee is senior, 80TTB is valid, but 80TTA above gets rejected
                    ceiling = tds_param_svc.get_parameter('80TTB_MAX_LIMIT', eval_date=eval_date)
                    if declared_val > ceiling:
                        approved_val = ceiling
                        val_status = 'exceeds_limit'
                        val_remarks = f"Section 80TTB Senior Citizen Deposit Interest claim capped at statutory limit of ₹{ceiling:,.2f}."
                else:
                    ceiling = tds_param_svc.get_parameter('80TTB_MAX_LIMIT', eval_date=eval_date)
                    if declared_val > ceiling:
                        approved_val = ceiling
                        val_status = 'exceeds_limit'
                        val_remarks = f"Section 80TTB Senior Citizen Deposit Interest claim capped at statutory limit of ₹{ceiling:,.2f}."


            elif cat == '80dd':
                is_severe = line.is_severe_disability or ('severe' in (line.description or '').lower())
                ceiling = tds_param_svc.get_80dd_limit(is_severe=is_severe, eval_date=eval_date)
                if declared_val > ceiling:
                    approved_val = ceiling
                    val_status = 'exceeds_limit'
                    val_remarks = f"Section 80DD Dependent Disability ({'Severe ≥80%' if is_severe else 'Normal ≥40%'}) claim capped at statutory limit of ₹{ceiling:,.2f}."


            elif cat == '24b':
                ceiling = tds_param_svc.get_home_loan_interest_limit(eval_date=eval_date)
                if declared_val > ceiling:
                    approved_val = ceiling
                    val_status = 'exceeds_limit'
                    val_remarks = f"Section 24(b) Self-Occupied Housing Interest claim capped at ₹{ceiling:,.2f}."

            elif cat == '80eea':
                # Invoke Section80EEAEligibilityService for employee home loan records
                home_loans = self.env['tds.employee.home.loan'].search([
                    ('employee_id', '=', declaration_record.employee_id.id),
                    ('financial_year_id', '=', declaration_record.financial_year_id.id)
                ], limit=1)
                if home_loans:
                    res = eea_svc.validate_eligibility(home_loans, eval_date=eval_date)
                    if res.is_eligible:
                        approved_val = min(declared_val, res.allowed_deduction)
                        val_status = 'valid' if declared_val <= res.allowed_deduction else 'exceeds_limit'
                        val_remarks = res.remarks
                    else:
                        approved_val = 0.0
                        val_status = 'ineligible_regime'
                        val_remarks = res.remarks
                else:
                    approved_val = 0.0
                    val_status = 'pending_proof'
                    val_remarks = "Section 80EEA Ineligible: No Housing Loan declaration record (tds.employee.home.loan) found for employee in this FY."

            elif cat == 'hra':
                # Landlord PAN Validation Rule (CBDT Circular): Mandatory if annual rent exceeds ₹1,00,000 p.a.
                if declared_val > 100000.0 and not line.landlord_pan:
                    val_remarks = "Landlord PAN is mandatory under CBDT circulars for annual rent claims exceeding ₹1,00,000 p.a. Please provide Landlord PAN."
                    val_status = 'pending_proof'
                    approved_val = 100000.0
                else:
                    val_remarks = f"HRA Rent Declaration of ₹{declared_val:,.2f} verified. Exemption calculation delegated to Section10HraExemptionService during payslip computation."
                    val_status = 'valid'

            elif cat == 'children_edu':
                # Statutory Ceiling: ₹100 per month per child for max 2 children (₹2,400 p.a.)
                monthly_limit = tds_param_svc.get_parameter('CHILDREN_EDU_ALLOWANCE_MONTHLY', eval_date=eval_date) or 100.0
                ceiling = monthly_limit * 12 * 2  # Max 2 children
                if declared_val > ceiling:
                    approved_val = ceiling
                    val_status = 'exceeds_limit'
                    val_remarks = f"Children Education Allowance exemption capped at statutory ceiling of ₹{ceiling:,.2f} (₹{monthly_limit:.0f}/month x 12 months x max 2 children)."

            elif cat == 'hostel':
                # Statutory Ceiling: ₹300 per month per child for max 2 children (₹7,200 p.a.)
                monthly_limit = tds_param_svc.get_parameter('HOSTEL_ALLOWANCE_MONTHLY', eval_date=eval_date) or 300.0
                ceiling = monthly_limit * 12 * 2  # Max 2 children
                if declared_val > ceiling:
                    approved_val = ceiling
                    val_status = 'exceeds_limit'
                    val_remarks = f"Hostel Expenditure Allowance exemption capped at statutory ceiling of ₹{ceiling:,.2f} (₹{monthly_limit:.0f}/month x 12 months x max 2 children)."

            elif cat == 'lta':
                # Delegate to Section10LtaExemptionService
                from .section10_lta_exemption_service import Section10LtaExemptionService
                lta_svc = Section10LtaExemptionService(self.env)
                lta_res = lta_svc.validate_and_calculate(
                    employee_id=declaration_record.employee_id.id,
                    declared_fare=declared_val,
                    eval_date=eval_date
                )
                approved_val = lta_res.exempt_amount
                val_status = 'valid' if lta_res.is_eligible and declared_val == approved_val else ('exceeds_limit' if lta_res.is_eligible else 'ineligible_regime')
                val_remarks = lta_res.remarks

            elif cat == 'leave_encashment':
                ceiling = tds_param_svc.get_leave_encashment_ceiling(eval_date=eval_date)
                if declared_val > ceiling:
                    approved_val = ceiling
                    val_status = 'exceeds_limit'
                    val_remarks = f"Leave Encashment Exemption capped at statutory ceiling of ₹{ceiling:,.2f}."


            elif cat == 'vrs':
                ceiling = tds_param_svc.get_parameter('VRS_EXEMPTION_CEILING', eval_date=eval_date)
                if declared_val > ceiling:
                    approved_val = ceiling
                    val_status = 'exceeds_limit'
                    val_remarks = f"VRS Compensation Exemption capped at statutory ceiling of ₹{ceiling:,.2f}."

            line.write({
                'approved_amount': approved_val,
                'validation_status': val_status,
                'validation_remarks': val_remarks,
            })
            line_results.append({'line_id': line.id, 'category': cat, 'approved_amount': approved_val, 'status': val_status})

        declaration_record._compute_totals()

        return EmployeeDeclarationValidationReport(
            declaration_id=declaration_record.id,
            regime_code=regime_code,
            is_compliant=is_compliant,
            total_declared=declaration_record.total_declared_amount,
            total_approved=declaration_record.total_approved_amount,
            line_results=line_results,
            error_messages=error_messages
        )
