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
        inc_decl = self.env['tds.employee.income.declaration'].search([
            ('employee_id', '=', employee.id),
            ('financial_year_id', '=', financial_year.id),
            ('state', 'in', ['submitted', 'approved'])
        ], limit=1)

        if not inc_decl:
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
