# -*- coding: utf-8 -*-
import logging
from odoo import fields, _
from odoo.exceptions import ValidationError
from ..base import BaseStatutoryService

_logger = logging.getLogger(__name__)


# Enterprise Parameter Mapping Table for regime-dependent & shared TDS parameters
TDS_PARAMETER_MAP = {
    # Standard Deduction
    'STD_DEDUCTION_NEW': 'HDS_IN_TDS_STD_DEDUCTION_NEW',
    'STD_DEDUCTION_OLD': 'HDS_IN_TDS_STD_DEDUCTION_OLD',
    # Section 87A Income Limit
    '87A_LIMIT_NEW': 'HDS_IN_TDS_87A_LIMIT_NEW',
    '87A_LIMIT_OLD': 'HDS_IN_TDS_87A_LIMIT_OLD',
    # Section 87A Max Rebate
    '87A_MAX_REBATE_NEW': 'HDS_IN_TDS_87A_MAX_REBATE_NEW',
    '87A_MAX_REBATE_OLD': 'HDS_IN_TDS_87A_MAX_REBATE_OLD',
    # Shared Cess Rate
    'HEALTH_CESS': 'HDS_IN_TDS_HEALTH_CESS',
    # Employer NPS Limits
    'NPS_LIMIT_NEW': 'HDS_IN_TDS_NPS_LIMIT_NEW',
    'NPS_LIMIT_OLD_PRIVATE': 'HDS_IN_TDS_NPS_LIMIT_OLD_PRIVATE',
    'NPS_LIMIT_OLD_GOVT': 'HDS_IN_TDS_NPS_LIMIT_OLD_GOVT',
    # Combined Employer Contribution Limit (PF + NPS + Superannuation)
    'EMPLOYER_CONTRIBUTION_LIMIT': 'HDS_IN_TDS_EMPLOYER_CONTRIBUTION_LIMIT',
    # Category A: Scalar Statutory Parameters (Simple Effective-Dated Statutory Constants)
    '80C_MAX_LIMIT': 'HDS_IN_TDS_80C_MAX_LIMIT',
    '80CCD1B_MAX_LIMIT': 'HDS_IN_TDS_80CCD1B_MAX_LIMIT',
    '80D_SELF_MAX_LIMIT': 'HDS_IN_TDS_80D_SELF_MAX_LIMIT',
    '80D_SELF_SENIOR_MAX_LIMIT': 'HDS_IN_TDS_80D_SELF_SENIOR_MAX_LIMIT',
    '80D_PARENTS_MAX_LIMIT': 'HDS_IN_TDS_80D_PARENTS_MAX_LIMIT',
    '80D_PARENTS_SENIOR_MAX_LIMIT': 'HDS_IN_TDS_80D_PARENTS_SENIOR_MAX_LIMIT',
    '80D_PREVENTIVE_CHECKUP_LIMIT': 'HDS_IN_TDS_80D_PREVENTIVE_CHECKUP_LIMIT',
    '80TTA_MAX_LIMIT': 'HDS_IN_TDS_80TTA_MAX_LIMIT',
    '80TTB_MAX_LIMIT': 'HDS_IN_TDS_80TTB_MAX_LIMIT',
    '80DD_NORMAL_LIMIT': 'HDS_IN_TDS_80DD_NORMAL_LIMIT',
    '80DD_SEVERE_LIMIT': 'HDS_IN_TDS_80DD_SEVERE_LIMIT',

    # Section 24(b) & Section 10 Exemptions (Category A Monetary Ceilings)
    '24B_HOME_LOAN_INTEREST_LIMIT': 'HDS_IN_TDS_24B_HOME_LOAN_INTEREST_LIMIT',

    # Category B: Eligibility-Based Statutory Features (Monetary ceiling stored as hr.rule.parameter,
    # BUT calculation engines MUST invoke employee eligibility validation services before applying ceiling)
    # E.g. Section 80EEA requires: Loan Sanctioned between 01-Apr-2019 and 31-Mar-2022, Stamp Value <= 45L, First-time Home Buyer.
    '80EEA_MAX_LIMIT': 'HDS_IN_TDS_80EEA_MAX_LIMIT',

    'HRA_METRO_PERCENT': 'HDS_IN_TDS_HRA_METRO_PERCENT',
    'HRA_NON_METRO_PERCENT': 'HDS_IN_TDS_HRA_NON_METRO_PERCENT',
    'HRA_RENT_EXCESS_BASIC_PERCENT': 'HDS_IN_TDS_HRA_RENT_EXCESS_BASIC_PERCENT',
    'CHILDREN_EDU_ALLOWANCE_MONTHLY': 'HDS_IN_TDS_CHILDREN_EDU_ALLOWANCE_MONTHLY',
    'HOSTEL_ALLOWANCE_MONTHLY': 'HDS_IN_TDS_HOSTEL_ALLOWANCE_MONTHLY',
    'LEAVE_ENCASHMENT_EXEMPTION_CEILING': 'HDS_IN_TDS_LEAVE_ENCASHMENT_EXEMPTION_CEILING',
    'VRS_EXEMPTION_CEILING': 'HDS_IN_TDS_VRS_EXEMPTION_CEILING',
}



class TdsParameterService(BaseStatutoryService):
    """
    Centralized Service Resolver for Indian TDS Engine Statutory Parameters & Masters.
    Provides regime-aware, effective-dated parameter lookups from hr.rule.parameter
    and structured query resolution for tds.financial.year, tds.tax.slab, and tds.surcharge masters.

    ARCHITECTURAL CLASSIFICATION FRAMEWORK:
    --------------------------------------
    1. Category A – Scalar Statutory Parameters:
       Simple statutory constants (e.g. Standard Deduction, Cess, Sec 80C limit, Sec 87A limit, Sec 24(b) limit)
       resolved directly via get_parameter().

    2. Category B – Eligibility-Based Statutory Features:
       Features where deduction eligibility depends on employee-specific facts (e.g. Sec 80EEA loan sanction date
       between 01/04/2019 and 31/03/2022, property value <= 45L, first-time home buyer).
       For Category B features, get_parameter() resolves the statutory ceiling, BUT downstream calculation engines
       MUST validate employee eligibility facts via declaration services BEFORE applying the deduction ceiling.

    All downstream TDS calculation services MUST resolve parameters through this service.
    """


    def get_parameter(self, code_or_key, eval_date=None, regime='new', employer_type='private', as_decimal=False):
        """
        Resolves a scalar statutory parameter by code, regime, and evaluation date.

        :param code_or_key: str (mapped short key like 'STD_DEDUCTION' or full parameter code)
        :param eval_date: datetime.date or str (defaults to today)
        :param regime: str ('new' or 'old')
        :param employer_type: str ('private', 'govt_central', 'govt_state')
        :param as_decimal: bool (if True and parameter is a rate, divides by 100.0)
        :return: float
        """
        if not eval_date:
            eval_date = fields.Date.today()
        elif isinstance(eval_date, str):
            eval_date = fields.Date.from_string(eval_date)

        regime_code = (regime or 'new').lower()

        # Dynamic regime-aware parameter key mapping
        resolved_code = code_or_key
        if code_or_key in ('STD_DEDUCTION', 'HDS_IN_TDS_STD_DEDUCTION'):
            resolved_code = 'HDS_IN_TDS_STD_DEDUCTION_NEW' if regime_code == 'new' else 'HDS_IN_TDS_STD_DEDUCTION_OLD'
        elif code_or_key in ('87A_LIMIT', 'HDS_IN_TDS_87A_LIMIT'):
            resolved_code = 'HDS_IN_TDS_87A_LIMIT_NEW' if regime_code == 'new' else 'HDS_IN_TDS_87A_LIMIT_OLD'
        elif code_or_key in ('87A_MAX_REBATE', 'HDS_IN_TDS_87A_MAX_REBATE'):
            resolved_code = 'HDS_IN_TDS_87A_MAX_REBATE_NEW' if regime_code == 'new' else 'HDS_IN_TDS_87A_MAX_REBATE_OLD'
        elif code_or_key in ('NPS_LIMIT', 'HDS_IN_TDS_NPS_LIMIT'):
            if regime_code == 'new':
                resolved_code = 'HDS_IN_TDS_NPS_LIMIT_NEW'
            elif 'govt' in (employer_type or '').lower():
                resolved_code = 'HDS_IN_TDS_NPS_LIMIT_OLD_GOVT'
            else:
                resolved_code = 'HDS_IN_TDS_NPS_LIMIT_OLD_PRIVATE'
        elif code_or_key in TDS_PARAMETER_MAP:
            resolved_code = TDS_PARAMETER_MAP[code_or_key]

        return self.env['hr.rule.parameter'].get_parameter(resolved_code, date=eval_date, as_decimal=as_decimal)

    def get_employer_nps_limit(self, regime='new', employer_type='private', eval_date=None, as_decimal=False):
        """
        Resolves Employer NPS statutory percentage limit based on regime and employer category.
        - New Regime: 14% for all employers.
        - Old Regime: 10% for Private/Other employers, 14% for Central/State Government.
        """
        return self.get_parameter('NPS_LIMIT', eval_date=eval_date, regime=regime, employer_type=employer_type, as_decimal=as_decimal)

    def get_combined_employer_contribution_limit(self, eval_date=None):
        """
        Resolves the statutory combined employer contribution ceiling under Section 17(2)(vii)
        for Employer PF + Employer NPS + Approved Superannuation (₹7,50,000 per annum).
        """
        return self.get_parameter('EMPLOYER_CONTRIBUTION_LIMIT', eval_date=eval_date, as_decimal=False)

    def get_80c_limit(self, eval_date=None):
        """Resolves Section 80C maximum allowable deduction ceiling (₹1,50,000)."""
        return self.get_parameter('80C_MAX_LIMIT', eval_date=eval_date)

    def get_80ccd1b_limit(self, eval_date=None):
        """Resolves Section 80CCD(1B) additional NPS deduction ceiling (₹50,000)."""
        return self.get_parameter('80CCD1B_MAX_LIMIT', eval_date=eval_date)

    def get_hra_percentage(self, is_metro=True, eval_date=None, as_decimal=False):
        """Resolves HRA exemption percentage (50% for Metro cities, 40% for Non-Metro)."""
        key = 'HRA_METRO_PERCENT' if is_metro else 'HRA_NON_METRO_PERCENT'
        return self.get_parameter(key, eval_date=eval_date, as_decimal=as_decimal)

    def get_80d_limit(self, is_senior=False, is_parents=False, eval_date=None):
        """Resolves Section 80D Health Insurance deduction ceiling based on beneficiary and senior citizen status."""
        if is_parents:
            key = '80D_PARENTS_SENIOR_MAX_LIMIT' if is_senior else '80D_PARENTS_MAX_LIMIT'
        else:
            key = '80D_SELF_SENIOR_MAX_LIMIT' if is_senior else '80D_SELF_MAX_LIMIT'
        return self.get_parameter(key, eval_date=eval_date)

    def get_home_loan_interest_limit(self, eval_date=None):
        """Resolves Section 24(b) Self-Occupied Home Loan Interest deduction ceiling (₹2,00,000)."""
        return self.get_parameter('24B_HOME_LOAN_INTEREST_LIMIT', eval_date=eval_date)

    def get_leave_encashment_ceiling(self, eval_date=None):
        """Resolves Section 10(10AA) Leave Encashment exemption ceiling for non-government employees (₹25,00,000)."""
        return self.get_parameter('LEAVE_ENCASHMENT_EXEMPTION_CEILING', eval_date=eval_date)

    def get_80dd_limit(self, is_severe=False, eval_date=None):
        """
        Resolves Section 80DD Dependent Disability deduction statutory ceiling.
        - Severe Disability (≥80%): HDS_IN_TDS_80DD_SEVERE_LIMIT (₹1,25,000)
        - Normal Disability (≥40% & <80%): HDS_IN_TDS_80DD_NORMAL_LIMIT (₹75,000)
        """
        key = '80DD_SEVERE_LIMIT' if is_severe else '80DD_NORMAL_LIMIT'
        return self.get_parameter(key, eval_date=eval_date)



    def get_financial_year(self, eval_date=None, company=None):
        """
        Resolves active tds.financial.year master record covering eval_date.
        Raises ValidationError if no active Financial Year is configured for eval_date.
        Silent fallback to previous Financial Year is strictly prohibited to prevent stale TDS deductions.
        """
        if not eval_date:
            eval_date = fields.Date.today()
        elif isinstance(eval_date, str):
            eval_date = fields.Date.from_string(eval_date)

        company = company or self.env.company
        if company and company.hds_in_default_tax_year:
            default_fy = company.hds_in_default_tax_year
            if default_fy.active and not default_fy.is_closed:
                if default_fy.start_date <= eval_date <= default_fy.end_date:
                    return default_fy

        domain = [
            ('active', '=', True),
            ('start_date', '<=', eval_date),
            ('end_date', '>=', eval_date),
            ('is_closed', '=', False),
        ]
        fy = self.env['tds.financial.year'].search(domain, limit=1)
        if not fy and company and company.hds_in_default_tax_year and company.hds_in_default_tax_year.active:
            fy = company.hds_in_default_tax_year

        if not fy:
            raise ValidationError(
                _(f"No active Financial Year configuration exists covering evaluation date {eval_date}. "
                  f"Please generate and configure the required Financial Year using the Financial Year Roll-Over Wizard "
                  f"before processing payroll or managing tax declarations.")
            )
        return fy



    def get_tax_slabs(self, financial_year=None, regime='new', eval_date=None):
        """
        Retrieves ordered income tax slab records for the target financial year and tax regime.

        :param financial_year: tds.financial.year recordset or ID (optional)
        :param regime: str ('new' or 'old')
        :param eval_date: datetime.date or str
        :return: recordset of tds.tax.slab
        """
        if not financial_year:
            financial_year = self.get_financial_year(eval_date=eval_date)

        regime_code = (regime or 'new').lower()
        domain = [
            ('financial_year_id', '=', financial_year.id if hasattr(financial_year, 'id') else financial_year),
            ('regime_code', '=', regime_code),
            ('active', '=', True),
        ]
        slabs = self.env['tds.tax.slab'].search(domain, order='income_from asc, sequence asc')
        if not slabs:
            _logger.warning(
                "TdsParameterService: No active tax slabs found for FY '%s', Regime '%s'.",
                getattr(financial_year, 'name', financial_year), regime_code
            )
        return slabs

    def get_surcharge_slabs(self, financial_year=None, regime='new', eval_date=None):
        """
        Retrieves ordered surcharge slab records for the target financial year and tax regime.

        :param financial_year: tds.financial.year recordset or ID (optional)
        :param regime: str ('new' or 'old')
        :param eval_date: datetime.date or str
        :return: recordset of tds.surcharge
        """
        if not financial_year:
            financial_year = self.get_financial_year(eval_date=eval_date)

        regime_code = (regime or 'new').lower()
        domain = [
            ('financial_year_id', '=', financial_year.id if hasattr(financial_year, 'id') else financial_year),
            ('regime_code', '=', regime_code),
            ('active', '=', True),
        ]
        surcharges = self.env['tds.surcharge'].search(domain, order='income_from asc, sequence asc')
        return surcharges
