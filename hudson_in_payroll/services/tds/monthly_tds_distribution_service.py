# -*- coding: utf-8 -*-
import logging
from odoo import fields
from odoo.exceptions import ValidationError
from ..base import BaseStatutoryService
from .previous_employer_tds_service import PreviousEmployerTdsService
from .current_financial_year_tds_service import CurrentFinancialYearTdsService
from .payroll_period_service import PayrollPeriodService

_logger = logging.getLogger(__name__)


class MonthlyTDSDistributionResult:
    """
    Data Transfer Object (DTO) holding monthly TDS distribution & current payslip withholding details.
    """
    def __init__(self, total_annual_tax_liability, ytd_tds_deducted, prev_employer_tds,
                 total_tds_paid_so_far, remaining_annual_tax_liability, remaining_payroll_periods,
                 current_month_tds):
        self.total_annual_tax_liability = total_annual_tax_liability
        self.ytd_tds_deducted = ytd_tds_deducted
        self.prev_employer_tds = prev_employer_tds
        self.total_tds_paid_so_far = total_tds_paid_so_far
        self.remaining_annual_tax_liability = remaining_annual_tax_liability
        self.remaining_payroll_periods = remaining_payroll_periods
        self.current_month_tds = current_month_tds


class MonthlyTDSDistributionService(BaseStatutoryService):
    """
    Phase 10 Service: Monthly TDS Distribution Engine Service.
    Distributes net remaining annual tax liability dynamically across remaining payroll periods in the Financial Year.
    Considers YTD TDS deducted on current employer payslips and previous employer TDS from Form 12B.
    Formula:
    1. Total TDS Paid So Far = YTD Current Employer TDS + Previous Employer TDS
    2. Remaining Liability = max(0.0, Total Annual Tax Liability - Total TDS Paid So Far)
    3. Current Month TDS = Remaining Liability / Remaining Payroll Periods (including current period)
    """

    def calculate_monthly_tds(self, employee, financial_year, total_annual_tax_liability, eval_date=None):
        """
        Calculates monthly TDS withholding for the current payslip evaluation period.

        :param employee: hr.employee record
        :param financial_year: tds.financial.year record
        :param total_annual_tax_liability: float (Total projected annual tax liability after cess)
        :param eval_date: Date (optional)
        :return: MonthlyTDSDistributionResult
        """
        _logger.warning("Entering MonthlyTDSDistributionService.calculate_monthly_tds for employee '%s' (Total Annual Tax Liability: %s, Eval Date: %s)", getattr(employee, 'name', 'Unknown'), total_annual_tax_liability, eval_date)

        try:
            if not employee:
                raise ValidationError("Monthly TDS Distribution Error: Employee record is required.")
            if not financial_year:
                raise ValidationError("Monthly TDS Distribution Error: Financial Year record is required.")
            if total_annual_tax_liability is None:
                raise ValidationError("Monthly TDS Distribution Error: Final Annual Tax Liability is required.")

            eval_date = eval_date or fields.Date.today()

            # 1. Resolve Previous Employer TDS via PreviousEmployerTdsService
            prev_tds_svc = PreviousEmployerTdsService(self.env)
            prev_employer_tds = prev_tds_svc.get_previous_employer_tds(employee, financial_year)

            # 2. Resolve Current Financial Year YTD TDS via CurrentFinancialYearTdsService
            ytd_tds_svc = CurrentFinancialYearTdsService(self.env)
            ytd_tds_deducted = ytd_tds_svc.get_ytd_tds_deducted(employee, financial_year)

            # 3. Resolve Remaining Payroll Periods via PayrollPeriodService
            period_svc = PayrollPeriodService(self.env)
            remaining_periods = period_svc.calculate_remaining_periods(employee, financial_year, eval_date=eval_date)

            # 4. Determine Remaining Annual Liability (with Zero Floor)
            total_tds_paid_so_far = ytd_tds_deducted + prev_employer_tds
            remaining_annual_tax = max(0.0, total_annual_tax_liability - total_tds_paid_so_far)

            # 5. Calculate Current Month TDS Withholding
            if remaining_annual_tax <= 0:
                current_month_tds = 0.0
            else:
                current_month_tds = round(remaining_annual_tax / remaining_periods, 2)

            _logger.info(
                "[TDS TRACE] Phase: Monthly Distribution | Service: MonthlyTDSDistributionService | Record ID: %s | Employee: %s | FY: %s | Field: current_month_tds | Old Value: N/A | New Value: ₹%s | Target Model: hr.payslip.line | DB Read: True | Calculation Result: AnnualTax=₹%s, PaidSoFar=₹%s (PrevTDS=₹%s, YTDTDS=₹%s), RemainingTax=₹%s, RemainingPeriods=%s, CurrentMonthTDS=₹%s",
                employee.id if employee else 'N/A', employee.name if employee else 'N/A', financial_year.name if financial_year else 'N/A',
                current_month_tds, total_annual_tax_liability, total_tds_paid_so_far, prev_employer_tds, ytd_tds_deducted,
                remaining_annual_tax, remaining_periods, current_month_tds
            )

            return MonthlyTDSDistributionResult(
                total_annual_tax_liability=total_annual_tax_liability,
                ytd_tds_deducted=ytd_tds_deducted,
                prev_employer_tds=prev_employer_tds,
                total_tds_paid_so_far=total_tds_paid_so_far,
                remaining_annual_tax_liability=remaining_annual_tax,
                remaining_payroll_periods=remaining_periods,
                current_month_tds=current_month_tds
            )
        except Exception as exc:
            _logger.warning("Exception inside MonthlyTDSDistributionService.calculate_monthly_tds: %s", exc, exc_info=True)
            raise
