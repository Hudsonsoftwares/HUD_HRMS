# -*- coding: utf-8 -*-
import logging
from ..base import BaseStatutoryService

_logger = logging.getLogger(__name__)


class CurrentFinancialYearTdsService(BaseStatutoryService):
    """
    Phase 10 Service: Current Financial Year TDS Service.
    Queries confirmed/done payslips for the employee within the Financial Year boundaries
    and sums YTD TDS withheld by current employer.
    """

    def get_ytd_tds_deducted(self, employee, financial_year):
        """
        Retrieves total YTD TDS deducted on current employer payslips.

        :param employee: hr.employee record
        :param financial_year: tds.financial.year record
        :return: float (YTD Current Employer TDS Deducted)
        """
        if not employee or not financial_year:
            return 0.0

        fy_start = financial_year.start_date
        fy_end = financial_year.end_date

        payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', fy_start),
            ('date_to', '<=', fy_end),
            ('state', 'in', ['done', 'paid'])
        ])

        ytd_tds = 0.0
        for slip in payslips:
            for line in slip.line_ids:
                if (line.code or '').upper() in ('TDS', 'HDS_IN_TDS', 'INCOME_TAX'):
                    ytd_tds += abs(line.total or 0.0)

        return ytd_tds
