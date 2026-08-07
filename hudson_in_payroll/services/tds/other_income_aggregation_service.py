# -*- coding: utf-8 -*-
import logging
from ..base import BaseStatutoryService

_logger = logging.getLogger(__name__)


class OtherIncomeAggregationResult:
    """
    Data Transfer Object (DTO) holding aggregated non-payroll income from other sources & house property.
    """
    def __init__(self, savings_interest=0.0, fd_interest=0.0, dividend_income=0.0,
                 other_sources_misc=0.0, total_other_sources=0.0,
                 gross_let_out_rent=0.0, municipal_taxes=0.0, nav=0.0,
                 property_std_deduction=0.0, let_out_interest=0.0,
                 net_house_property_income_loss=0.0, total_other_income=0.0, has_declaration=False):
        self.savings_interest = savings_interest
        self.fd_interest = fd_interest
        self.dividend_income = dividend_income
        self.other_sources_misc = other_sources_misc
        self.total_other_sources = total_other_sources
        self.gross_let_out_rent = gross_let_out_rent
        self.municipal_taxes = municipal_taxes
        self.nav = nav
        self.property_std_deduction = property_std_deduction
        self.let_out_interest = let_out_interest
        self.net_house_property_income_loss = net_house_property_income_loss
        self.total_other_income = total_other_income
        self.has_declaration = has_declaration


class OtherIncomeAggregationService(BaseStatutoryService):
    """
    Phase 4 Service: Other Income Aggregation Service.
    Aggregates non-payroll Category A regime-neutral declared incomes:
    1. Income from Other Sources (Savings Interest, FD Interest, Dividends, Miscellaneous)
    2. Income / Loss from Let-Out House Property (Gross Rent - Municipal Taxes - 30% NAV - Loan Interest)
    """

    def aggregate_other_income(self, employee, financial_year):
        """
        Aggregates non-payroll income for the employee in the specified Financial Year.

        :param employee: hr.employee record
        :param financial_year: tds.financial.year record
        :return: OtherIncomeAggregationResult
        """
        inc_decl = self.env['tds.employee.income.declaration'].sudo().search([
            ('employee_id', '=', employee.id),
            ('financial_year_id', '=', financial_year.id),
        ], limit=1)

        _logger.warning("========== OTHER INCOME AGGREGATION ==========")
        _logger.warning(
            "Employee: %s | FY: %s",
            employee.name if employee else "Unknown",
            financial_year.name if financial_year else "Unknown"
        )
        _logger.warning(
            "Declaration Found: %s",
            inc_decl.id if inc_decl else "None"
        )
        _logger.warning(
            "Savings Interest: %s",
            inc_decl.savings_bank_interest if inc_decl else 0.0
        )
        _logger.warning(
            "FD Interest: %s",
            inc_decl.fixed_deposit_interest if inc_decl else 0.0
        )
        _logger.warning(
            "Dividend Income: %s",
            inc_decl.dividend_income if inc_decl else 0.0
        )
        _logger.warning(
            "Other Misc Income: %s",
            inc_decl.other_sources_income if inc_decl else 0.0
        )
        _logger.warning(
            "Gross Rent: %s",
            inc_decl.annual_let_out_rent if inc_decl else 0.0
        )
        _logger.warning(
            "Municipal Tax: %s",
            inc_decl.municipal_taxes_paid if inc_decl else 0.0
        )
        _logger.warning(
            "Let Out Interest: %s",
            inc_decl.let_out_interest_paid if inc_decl else 0.0
        )

        if not inc_decl:
            _logger.warning("Total Other Sources: 0.0")
            _logger.warning("Net House Property Income/Loss: 0.0")
            _logger.warning("Total Other Income Returned: 0.0")
            _logger.warning("=============================================")
            return OtherIncomeAggregationResult(has_declaration=False)

        savings_interest = inc_decl.savings_bank_interest or 0.0
        fd_interest = inc_decl.fixed_deposit_interest or 0.0
        dividend_income = inc_decl.dividend_income or 0.0
        other_misc = inc_decl.other_sources_income or 0.0
        total_other_sources = savings_interest + fd_interest + dividend_income + other_misc

        gross_rent = inc_decl.annual_let_out_rent or 0.0
        munc_tax = inc_decl.municipal_taxes_paid or 0.0
        nav = max(0.0, gross_rent - munc_tax)
        prop_std_ded = nav * 0.30  # Section 24(a) 30% NAV statutory repair allowance
        let_out_interest = inc_decl.let_out_interest_paid or 0.0

        net_property = nav - prop_std_ded - let_out_interest

        total_other_income = total_other_sources + net_property

        _logger.warning(
            "Total Other Sources: %s",
            total_other_sources
        )
        _logger.warning(
            "Net House Property Income/Loss: %s",
            net_property
        )
        _logger.warning(
            "Total Other Income Returned: %s",
            total_other_income
        )
        _logger.warning("=============================================")

        return OtherIncomeAggregationResult(
            savings_interest=savings_interest,
            fd_interest=fd_interest,
            dividend_income=dividend_income,
            other_sources_misc=other_misc,
            total_other_sources=total_other_sources,
            gross_let_out_rent=gross_rent,
            municipal_taxes=munc_tax,
            nav=nav,
            property_std_deduction=prop_std_ded,
            let_out_interest=let_out_interest,
            net_house_property_income_loss=net_property,
            total_other_income=total_other_income,
            has_declaration=True
        )
