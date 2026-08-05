# -*- coding: utf-8 -*-
import logging
from odoo import fields
from ..base import BaseStatutoryService
from .annual_income_projection_service import AnnualIncomeProjectionService
from .deduction_calculation_service import DeductionCalculationService
from .taxable_income_service import TaxableIncomeService
from .income_tax_slab_service import IncomeTaxSlabService
from .rebate_engine_service import RebateEngineService
from .surcharge_engine_service import SurchargeEngineService
from .health_education_cess_service import HealthEducationCessService
from .monthly_tds_distribution_service import MonthlyTDSDistributionService

_logger = logging.getLogger(__name__)


class TdsComputationResult:
    """
    Data Transfer Object (DTO) holding the complete end-to-end statutory audit trace
    produced by the Master TDS Orchestration Engine.
    """
    def __init__(self, employee_id, financial_year_id, regime_code, regime_name,
                 annual_income_projection, deduction_calculation, taxable_income,
                 income_tax_slab, rebate_engine, surcharge_engine, health_education_cess,
                 monthly_tds_distribution):
        self.employee_id = employee_id
        self.financial_year_id = financial_year_id
        self.regime_code = regime_code
        self.regime_name = regime_name
        self.annual_income_projection = annual_income_projection
        self.deduction_calculation = deduction_calculation
        self.taxable_income = taxable_income
        self.income_tax_slab = income_tax_slab
        self.rebate_engine = rebate_engine
        self.surcharge_engine = surcharge_engine
        self.health_education_cess = health_education_cess
        self.monthly_tds_distribution = monthly_tds_distribution

    @property
    def current_month_tds(self):
        """Current month TDS withholding amount."""
        return self.monthly_tds_distribution.current_month_tds

    @property
    def total_annual_tax_liability(self):
        """Total projected annual tax liability after cess."""
        return self.health_education_cess.total_annual_tax_liability


class TdsOrchestrationEngine(BaseStatutoryService):
    """
    Enterprise TDS Orchestration Engine.
    Acts as the thin entry point for salary rule execution during payslip computation.
    Coordinates all specialized TDS services following the strict statutory sequence:
    1. Resolve Financial Year
    2. Resolve Employee Tax Regime
    3. Project Annual Income (Regime-Neutral)
    4. Route Regime & Calculate Approved Deductions
    5. Compute Net Taxable Income
    6. Compute Base Tax via Income Tax Slabs
    7. Apply Section 87A Tax Rebate
    8. Apply Range-Based Surcharge
    9. Apply Health & Education Cess
    10. Determine Final Annual Tax Liability
    11. Distribute Net Liability into Monthly TDS Withholding
    """

    def hds_in_compute_tds(self, employee, eval_date=None):
        """
        Master Entry Point for Payslip Statutory TDS Calculation.

        :param employee: hr.employee record
        :param eval_date: Date (optional payslip evaluation date)
        :return: TdsComputationResult
        """
        _logger.warning("Entering TdsOrchestrationEngine for employee '%s' (Eval Date: %s)", getattr(employee, 'name', 'Unknown'), eval_date)
        eval_date = eval_date or fields.Date.today()


        # Step 1 to 3: Annual Income Projection & Tax Regime Resolution (Phase 4 Master Service)
        _logger.warning("Before AnnualIncomeProjectionService")
        projection_svc = AnnualIncomeProjectionService(self.env)
        annual_projection = projection_svc.project_annual_income(employee, eval_date=eval_date)
        _logger.warning(
            "After AnnualIncomeProjectionService | Gross Payroll Income: %s, Previous Employer Income: %s, Other Income: %s, Gross Total Income: %s",
            annual_projection.projected_annual_salary,
            annual_projection.previous_employer_income.taxable_salary,
            annual_projection.other_income_aggregation.total_other_income,
            annual_projection.gross_total_income
        )

        financial_year_id = annual_projection.financial_year_id
        financial_year = self.env['tds.financial.year'].browse(financial_year_id)
        regime_code = annual_projection.regime_code
        regime_name = annual_projection.regime_name
        regime_context = annual_projection.regime_context
        gti = annual_projection.gross_total_income

        # Step 4: Regime Routing & Deduction Calculation
        _logger.warning("Before DeductionCalculationService")
        deduction_svc = DeductionCalculationService(self.env)
        deduction_calc = deduction_svc.calculate_deductions(
            employee=employee,
            financial_year=financial_year,
            regime_context=regime_context,
            eval_date=eval_date
        )
        _logger.warning(
            "After DeductionCalculationService | Standard Deduction: %s, Chapter VI-A Deductions: %s, HRA Exemption: %s, Home Loan Deduction: %s, Total Deductions: %s",
            deduction_calc.standard_deduction,
            deduction_calc.total_chapter_6a,
            deduction_calc.hra_exemption,
            deduction_calc.home_loan_interest_24b,
            deduction_calc.total_approved_deductions
        )

        # Step 5: Net Taxable Income Computation
        _logger.warning("Before TaxableIncomeService")
        taxable_svc = TaxableIncomeService(self.env)
        taxable_inc = taxable_svc.calculate_taxable_income(
            gross_total_income=gti,
            total_approved_deductions=deduction_calc.total_approved_deductions
        )
        _logger.warning(
            "After TaxableIncomeService | Taxable Income: %s",
            taxable_inc.net_taxable_income
        )

        # Step 6: Income Tax Slab Engine Computation
        _logger.warning("Before IncomeTaxSlabService")
        slab_svc = IncomeTaxSlabService(self.env)
        slab_calc = slab_svc.calculate_base_tax(
            net_taxable_income=taxable_inc.net_taxable_income,
            financial_year=financial_year,
            regime_code=regime_code
        )
        _logger.warning(
            "After IncomeTaxSlabService | Base Tax: %s",
            slab_calc.base_tax_liability
        )

        # Step 7: Section 87A Rebate Engine Application
        _logger.warning("Before RebateEngineService")
        rebate_svc = RebateEngineService(self.env)
        rebate_calc = rebate_svc.apply_rebate(
            net_taxable_income=taxable_inc.net_taxable_income,
            base_tax_liability=slab_calc.base_tax_liability,
            regime_code=regime_code,
            eval_date=eval_date
        )
        _logger.warning(
            "After RebateEngineService | 87A Rebate: %s, Tax After Rebate: %s",
            rebate_calc.rebate_applied,
            rebate_calc.tax_after_rebate
        )

        # Step 8: Range-Based Surcharge Engine Application
        _logger.warning("Before SurchargeEngineService")
        surcharge_svc = SurchargeEngineService(self.env)
        surcharge_calc = surcharge_svc.calculate_surcharge(
            net_taxable_income=taxable_inc.net_taxable_income,
            tax_after_rebate=rebate_calc.tax_after_rebate,
            financial_year=financial_year,
            regime_code=regime_code
        )
        _logger.warning(
            "After SurchargeEngineService | Surcharge Amount: %s",
            surcharge_calc.surcharge_amount
        )

        # Step 9 & 10: Health & Education Cess Engine & Annual Tax Liability
        _logger.warning("Before HealthEducationCessService")
        cess_svc = HealthEducationCessService(self.env)
        cess_calc = cess_svc.calculate_cess(
            tax_plus_surcharge=surcharge_calc.tax_plus_surcharge,
            eval_date=eval_date
        )
        _logger.warning(
            "After HealthEducationCessService | Cess Amount: %s, Final Annual Tax: %s",
            cess_calc.cess_amount,
            cess_calc.total_annual_tax_liability
        )

        # Step 11: Monthly TDS Distribution Engine Computation
        _logger.warning("Before MonthlyTDSDistributionService")
        monthly_svc = MonthlyTDSDistributionService(self.env)
        monthly_tds = monthly_svc.calculate_monthly_tds(
            employee=employee,
            financial_year=financial_year,
            total_annual_tax_liability=cess_calc.total_annual_tax_liability,
            eval_date=eval_date
        )
        _logger.warning(
            "After MonthlyTDSDistributionService | Previous Employer TDS: %s, Current FY TDS: %s, Remaining Liability: %s, Remaining Payroll Periods: %s, Current Month TDS: %s",
            monthly_tds.prev_employer_tds,
            monthly_tds.ytd_tds_deducted,
            monthly_tds.remaining_annual_tax_liability,
            monthly_tds.remaining_payroll_periods,
            monthly_tds.current_month_tds
        )

        summary_report = f"""
========================================================
HUDSON PAYROLL TDS COMPUTATION SUMMARY
========================================================

Tax Regime                 : {regime_code.upper()}

Gross Annual Income        : ₹{annual_projection.salary_projection.total_projected_current_salary:,.2f}
Previous Employer Income   : ₹{annual_projection.previous_employer_income.taxable_salary:,.2f}
Other Income               : ₹{annual_projection.other_income_aggregation.total_other_income:,.2f}
Gross Total Income         : ₹{annual_projection.gross_total_income:,.2f}

Standard Deduction         : ₹{deduction_calc.standard_deduction:,.2f}
80C                        : ₹{getattr(deduction_calc, 'chapter_6a_deductions', 0.0):,.2f}
80CCD(1B)                  : ₹0.00
80D                        : ₹0.00
HRA Exemption              : ₹{deduction_calc.hra_exemption:,.2f}
Home Loan                  : ₹{deduction_calc.home_loan_interest_24b:,.2f}

Total Deductions           : ₹{deduction_calc.total_allowable_deductions:,.2f}

Taxable Income             : ₹{taxable_inc.net_taxable_income:,.2f}

Base Tax                   : ₹{slab_calc.base_tax_liability:,.2f}

87A Rebate                 : ₹{rebate_calc.rebate_applied:,.2f}

Tax After Rebate           : ₹{rebate_calc.tax_after_rebate:,.2f}

Surcharge                  : ₹{surcharge_calc.surcharge_amount:,.2f}

Health & Education Cess    : ₹{cess_calc.cess_amount:,.2f}

Final Annual Tax           : ₹{cess_calc.total_annual_tax_liability:,.2f}

Previous Employer TDS      : ₹{monthly_tds.prev_employer_tds:,.2f}

Current FY TDS             : ₹{monthly_tds.ytd_tds_deducted:,.2f}

Remaining Tax Liability    : ₹{monthly_tds.remaining_annual_tax_liability:,.2f}

Remaining Payroll Periods  : {monthly_tds.remaining_payroll_periods}

Current Month TDS          : ₹{monthly_tds.current_month_tds:,.2f}

========================================================
"""
        _logger.warning(summary_report)


        return TdsComputationResult(
            employee_id=employee.id,
            financial_year_id=financial_year_id,
            regime_code=regime_code,
            regime_name=regime_name,
            annual_income_projection=annual_projection,
            deduction_calculation=deduction_calc,
            taxable_income=taxable_inc,
            income_tax_slab=slab_calc,
            rebate_engine=rebate_calc,
            surcharge_engine=surcharge_calc,
            health_education_cess=cess_calc,
            monthly_tds_distribution=monthly_tds
        )

