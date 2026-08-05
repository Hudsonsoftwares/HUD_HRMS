# -*- coding: utf-8 -*-
import logging
from odoo import fields
from ..base import BaseStatutoryService

_logger = logging.getLogger(__name__)


class PayrollPeriodService(BaseStatutoryService):
    """
    Phase 10 Service: Payroll Period Service.
    Dynamically determines the remaining payroll periods in the Financial Year (including current evaluation month).
    Supports:
    - Standard Financial Year (12 monthly periods April through March)
    - Mid-year joiners
    - Early resignations / departures before FY end
    """

    def calculate_remaining_periods(self, employee, financial_year, eval_date=None):
        """
        Calculates remaining payroll periods in Financial Year (inclusive of current month).

        :param employee: hr.employee record
        :param financial_year: tds.financial.year record
        :param eval_date: Date (optional payslip eval_date / date_to)
        :return: int (Remaining payroll periods, min 1)
        """
        eval_date = eval_date or fields.Date.today()
        if isinstance(eval_date, str):
            eval_date = fields.Date.from_string(eval_date)

        fy_start = financial_year.start_date
        fy_end = financial_year.end_date

        if eval_date < fy_start:
            return 12
        elif eval_date > fy_end:
            return 1

        fy_start_year = fy_start.year
        fy_start_month = fy_start.month
        eval_year = eval_date.year
        eval_month = eval_date.month

        # Calculate number of elapsed months in the FY including evaluation month
        elapsed_months = (eval_year - fy_start_year) * 12 + (eval_month - fy_start_month) + 1
        remaining_in_fy = max(1, min(12, 12 - elapsed_months + 1))

        # Check early resignation / departure date on employee record
        departure_date = (
            getattr(employee, 'departure_date', False) or
            getattr(employee, 'resignation_date', False)
        )

        if departure_date:
            if isinstance(departure_date, str):
                departure_date = fields.Date.from_string(departure_date)
            if fy_start <= departure_date <= fy_end:
                dep_year = departure_date.year
                dep_month = departure_date.month
                max_possible = (dep_year - eval_year) * 12 + (dep_month - eval_month) + 1
                return max(1, min(remaining_in_fy, max_possible))

        return remaining_in_fy
