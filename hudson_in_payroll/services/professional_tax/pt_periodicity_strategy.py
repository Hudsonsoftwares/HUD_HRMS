# -*- coding: utf-8 -*-
import logging
from abc import ABC, abstractmethod
from datetime import date
from odoo import fields
from ..payroll.payroll_wage_aggregation_service import PayrollWageAggregationService

_logger = logging.getLogger(__name__)


class AbstractPTPeriodicityStrategy(ABC):
    """
    Abstract Base Class for Professional Tax Periodicity Strategies.
    Encapsulates window resolution, deduction schedule determination, and wage aggregation logic.
    """

    @abstractmethod
    def get_periodicity_code(self) -> str:
        """Returns the periodicity code matching pt.state.slab (e.g., 'monthly', 'half_yearly')."""
        pass

    @abstractmethod
    def resolve_aggregation_window(self, eval_date: date) -> tuple:
        """Resolves period (start_date, end_date) for a given evaluation date."""
        pass

    def should_deduct(self, eval_date: date, slab=None) -> bool:
        """
        Determines whether PT should be deducted for eval_date based on slab configuration fields.
        Falls back to default periodicity rules if slab configuration fields are unset.
        """
        if isinstance(eval_date, str):
            eval_date = fields.Date.from_string(eval_date)
        if not eval_date:
            eval_date = fields.Date.today()

        m = eval_date.month

        # Handle both ProfessionalTaxSlabResult wrappers and raw pt.state.slab records
        slab_rec = getattr(slab, 'slab_record', slab)
        sched_type = getattr(slab_rec, 'deduction_schedule_type', None) if slab_rec else None
        ded_month_raw = getattr(slab_rec, 'deduction_month', None) if slab_rec else None
        override_m_raw = getattr(slab_rec, 'override_month', None) if slab_rec else None

        # Check special override month first
        if override_m_raw:
            try:
                if int(str(override_m_raw).strip()) == m:
                    return True
            except (ValueError, TypeError):
                pass

        if sched_type == 'every_payroll':
            return True

        if sched_type == 'specific_month':
            if ded_month_raw:
                try:
                    return m == int(str(ded_month_raw).strip())
                except (ValueError, TypeError):
                    pass
            return False

        if sched_type == 'end_of_period':
            if ded_month_raw:
                try:
                    return m == int(str(ded_month_raw).strip())
                except (ValueError, TypeError):
                    pass
            periodicity = self.get_periodicity_code()
            if periodicity == 'half_yearly':
                return m in (9, 3)
            elif periodicity == 'quarterly':
                return m in (6, 9, 12, 3)
            elif periodicity == 'annual':
                return m == 3
            return True

        if sched_type == 'beginning_of_period':
            if ded_month_raw:
                try:
                    return m == int(str(ded_month_raw).strip())
                except (ValueError, TypeError):
                    pass
            periodicity = self.get_periodicity_code()
            if periodicity == 'half_yearly':
                return m in (4, 10)
            elif periodicity == 'quarterly':
                return m in (4, 7, 10, 1)
            elif periodicity == 'annual':
                return m == 4
            return True

        return True


class MonthlyPTStrategy(AbstractPTPeriodicityStrategy):
    """Monthly Professional Tax Strategy (e.g. Maharashtra, Karnataka monthly)."""

    def get_periodicity_code(self) -> str:
        return 'monthly'

    def resolve_aggregation_window(self, eval_date: date) -> tuple:
        if isinstance(eval_date, str):
            eval_date = fields.Date.from_string(eval_date)
        if not eval_date:
            eval_date = fields.Date.today()
        year = eval_date.year
        month = eval_date.month
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        return (date(year, month, 1), date(year, month, last_day))

    def is_deduction_period(self, eval_date: date, slab=None) -> bool:
        return self.should_deduct(eval_date, slab=slab)

    def calculate_wage_basis(
        self,
        env,
        employee,
        eval_date: date,
        current_slip=None,
        current_slip_gross=0.0,
        company=None,
        **kwargs
    ) -> float:
        return float(current_slip_gross or 0.0)


class HalfYearlyPTStrategy(AbstractPTPeriodicityStrategy):
    """Half-Yearly Professional Tax Strategy (e.g. Kerala, Tamil Nadu)."""

    def get_periodicity_code(self) -> str:
        return 'half_yearly'

    def resolve_aggregation_window(self, eval_date: date) -> tuple:
        if isinstance(eval_date, str):
            eval_date = fields.Date.from_string(eval_date)
        if not eval_date:
            eval_date = fields.Date.today()

        month = eval_date.month
        year = eval_date.year

        # Indian Statutory Half-Year Windows:
        # H1: April 1 to September 30
        # H2: October 1 to March 31 of following year
        if 4 <= month <= 9:
            start_d = date(year, 4, 1)
            end_d = date(year, 9, 30)
        elif month >= 10:
            start_d = date(year, 10, 1)
            end_d = date(year + 1, 3, 31)
        else:  # month in (1, 2, 3)
            start_d = date(year - 1, 10, 1)
            end_d = date(year, 3, 31)

        return (start_d, end_d)

    def is_deduction_period(self, eval_date: date, slab=None) -> bool:
        return self.should_deduct(eval_date, slab=slab)

    def calculate_wage_basis(
        self,
        env,
        employee,
        eval_date: date,
        current_slip=None,
        current_slip_gross=0.0,
        company=None,
        period_schedule=None
    ) -> float:
        if period_schedule:
            from .pt_period_config_service import PTPeriodScheduleService
            sched_service = PTPeriodScheduleService(env)
            start_d, end_d = sched_service.resolve_period_window(period_schedule, eval_date=eval_date)
        else:
            start_d, end_d = self.resolve_aggregation_window(eval_date)

        agg_service = PayrollWageAggregationService(env)
        return agg_service.get_aggregated_wage(
            employee=employee,
            start_date=start_d,
            end_date=end_d,
            category_code="GROSS",
            company=company,
            current_slip=current_slip,
            current_slip_gross=current_slip_gross
        )


class QuarterlyPTStrategy(AbstractPTPeriodicityStrategy):
    """Quarterly Professional Tax Strategy (e.g. Madhya Pradesh quarterly)."""

    def get_periodicity_code(self) -> str:
        return 'quarterly'

    def resolve_aggregation_window(self, eval_date: date) -> tuple:
        if isinstance(eval_date, str):
            eval_date = fields.Date.from_string(eval_date)
        if not eval_date:
            eval_date = fields.Date.today()

        month = eval_date.month
        year = eval_date.year

        # Indian Financial Year Quarters:
        # Q1: Apr-Jun, Q2: Jul-Sep, Q3: Oct-Dec, Q4: Jan-Mar
        if 4 <= month <= 6:
            return (date(year, 4, 1), date(year, 6, 30))
        elif 7 <= month <= 9:
            return (date(year, 7, 1), date(year, 9, 30))
        elif 10 <= month <= 12:
            return (date(year, 10, 1), date(year, 12, 31))
        else:
            return (date(year, 1, 1), date(year, 3, 31))

    def is_deduction_period(self, eval_date: date, slab=None) -> bool:
        return self.should_deduct(eval_date, slab=slab)

    def calculate_wage_basis(
        self,
        env,
        employee,
        eval_date: date,
        current_slip=None,
        current_slip_gross=0.0,
        company=None,
        period_schedule=None
    ) -> float:
        if period_schedule:
            from .pt_period_config_service import PTPeriodScheduleService
            sched_service = PTPeriodScheduleService(env)
            start_d, end_d = sched_service.resolve_period_window(period_schedule, eval_date=eval_date)
        else:
            start_d, end_d = self.resolve_aggregation_window(eval_date)

        agg_service = PayrollWageAggregationService(env)
        return agg_service.get_aggregated_wage(
            employee=employee,
            start_date=start_d,
            end_date=end_d,
            category_code="GROSS",
            company=company,
            current_slip=current_slip,
            current_slip_gross=current_slip_gross
        )


class AnnualPTStrategy(AbstractPTPeriodicityStrategy):
    """Annual Professional Tax Strategy."""

    def get_periodicity_code(self) -> str:
        return 'annual'

    def resolve_aggregation_window(self, eval_date: date) -> tuple:
        if isinstance(eval_date, str):
            eval_date = fields.Date.from_string(eval_date)
        if not eval_date:
            eval_date = fields.Date.today()

        year = eval_date.year
        if eval_date.month >= 4:
            return (date(year, 4, 1), date(year + 1, 3, 31))
        else:
            return (date(year - 1, 4, 1), date(year, 3, 31))

    def is_deduction_period(self, eval_date: date, slab=None) -> bool:
        return self.should_deduct(eval_date, slab=slab)

    def calculate_wage_basis(
        self,
        env,
        employee,
        eval_date: date,
        current_slip=None,
        current_slip_gross=0.0,
        company=None
    ) -> float:
        start_d, end_d = self.resolve_aggregation_window(eval_date)
        agg_service = PayrollWageAggregationService(env)
        return agg_service.get_aggregated_wage(
            employee=employee,
            start_date=start_d,
            end_date=end_d,
            category_code="GROSS",
            company=company,
            current_slip=current_slip,
            current_slip_gross=current_slip_gross
        )


class PTPeriodicityStrategyRegistry:
    """
    Factory & Registry for Professional Tax Periodicity Strategies.
    Decouples ProfessionalTaxService from periodicity-specific code branches.
    """

    _strategies = {
        'monthly': MonthlyPTStrategy(),
        'half_yearly': HalfYearlyPTStrategy(),
        'quarterly': QuarterlyPTStrategy(),
        'annual': AnnualPTStrategy(),
    }

    @classmethod
    def get_strategy(cls, periodicity_code) -> AbstractPTPeriodicityStrategy:
        """
        Retrieves matching strategy instance by periodicity code.
        Defaults to MonthlyPTStrategy if code is unrecognised.
        """
        code = str(periodicity_code).strip().lower() if periodicity_code else 'monthly'
        return cls._strategies.get(code, cls._strategies['monthly'])
