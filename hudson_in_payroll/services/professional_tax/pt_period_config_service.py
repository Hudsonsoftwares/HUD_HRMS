# -*- coding: utf-8 -*-
import logging
from datetime import date
import calendar
from odoo import fields

_logger = logging.getLogger(__name__)


class PTPeriodScheduleService:
    """
    Domain Service for Professional Tax Period Schedule Resolution.
    Decoupled from salary slab amount matching (pt.state.slab).

    Responsibilities:
    - Locate active pt.period.schedule record for state, company, and evaluation date.
    - Calculate exact statutory date range (start_date, end_date) for the matching period window.
    - Determine if evaluation date is a statutory deduction payroll date for the schedule.
    """

    def __init__(self, env):
        self.env = env

    def resolve_schedule(self, state, company=None, eval_date=None):
        """
        Resolves the active pt.period.schedule record matching state, company, and eval_date.

        :param state: res.country.state recordset
        :param company: res.company recordset
        :param eval_date: datetime.date or str
        :return: pt.period.schedule recordset (single record) or False
        """
        if not state:
            return False

        if not eval_date:
            eval_date = fields.Date.today()
        elif isinstance(eval_date, str):
            eval_date = fields.Date.from_string(eval_date)

        target_company = company or self.env.company
        month = eval_date.month

        # Build search domain for active schedules
        base_domain = [
            ('state_id', '=', state.id),
            ('active', '=', True),
            '|', ('date_from', '=', False), ('date_from', '<=', eval_date),
            '|', ('date_to', '=', False), ('date_to', '>=', eval_date),
            '|', ('company_id', '=', False), ('company_id', '=', target_company.id),
        ]

        schedules = self.env['pt.period.schedule'].search(base_domain)
        if not schedules:
            return False

        # Filter schedules whose window includes month
        matching_schedules = []
        for sched in schedules:
            start_m = int(sched.window_start_month or '1')
            end_m = int(sched.window_end_month or '12')

            if start_m <= end_m:
                if start_m <= month <= end_m:
                    matching_schedules.append(sched)
            else: # Crosses calendar year boundary (e.g. October 10 -> March 3)
                if month >= start_m or month <= end_m:
                    matching_schedules.append(sched)

        if not matching_schedules:
            # Fall back to first matching schedule for state
            return schedules[0]

        # Rank company-specific over global
        def rank_key(s):
            is_company = 1 if (company and s.company_id and s.company_id.id == company.id) else 0
            d_from = s.date_from or fields.Date.from_string('1900-01-01')
            return (is_company, d_from, s.id)

        sorted_schedules = sorted(matching_schedules, key=rank_key, reverse=True)
        return sorted_schedules[0]

    def resolve_period_window(self, schedule, eval_date=None):
        """
        Calculates exact (start_date, end_date) date tuple for period schedule window.

        :param schedule: pt.period.schedule recordset
        :param eval_date: datetime.date or str
        :return: tuple of (start_date, end_date)
        """
        if not eval_date:
            eval_date = fields.Date.today()
        elif isinstance(eval_date, str):
            eval_date = fields.Date.from_string(eval_date)

        year = eval_date.year
        month = eval_date.month

        if not schedule:
            # Default monthly window
            last_day = calendar.monthrange(year, month)[1]
            return (date(year, month, 1), date(year, month, last_day))

        start_m = int(schedule.window_start_month or '1')
        end_m = int(schedule.window_end_month or '12')

        if start_m <= end_m:
            # Single calendar year window (e.g. April 4 -> September 9)
            start_d = date(year, start_m, 1)
            last_day = calendar.monthrange(year, end_m)[1]
            end_d = date(year, end_m, last_day)
        else:
            # Crosses calendar year boundary (e.g. October 10 -> March 3)
            if month >= start_m:
                start_d = date(year, start_m, 1)
                last_day = calendar.monthrange(year + 1, end_m)[1]
                end_d = date(year + 1, end_m, last_day)
            else: # month in (1, 2, 3)
                start_d = date(year - 1, start_m, 1)
                last_day = calendar.monthrange(year, end_m)[1]
                end_d = date(year, end_m, last_day)

        return (start_d, end_d)

    def should_deduct(self, schedule, eval_date=None):
        """
        Determines whether PT should be deducted for eval_date according to schedule configuration.

        :param schedule: pt.period.schedule recordset
        :param eval_date: datetime.date or str
        :return: bool
        """
        if not schedule:
            return True

        if not eval_date:
            eval_date = fields.Date.today()
        elif isinstance(eval_date, str):
            eval_date = fields.Date.from_string(eval_date)

        m = eval_date.month
        strategy_type = schedule.deduction_strategy or 'every_payroll'

        if strategy_type == 'every_payroll':
            return True

        if strategy_type == 'specific_month':
            if schedule.deduction_month:
                try:
                    return m == int(str(schedule.deduction_month).strip())
                except (ValueError, TypeError):
                    pass
            return False

        if strategy_type == 'end_of_period':
            target_m = int(schedule.window_end_month or '12')
            if schedule.deduction_month:
                try:
                    target_m = int(str(schedule.deduction_month).strip())
                except (ValueError, TypeError):
                    pass
            return m == target_m

        if strategy_type == 'beginning_of_period':
            target_m = int(schedule.window_start_month or '1')
            if schedule.deduction_month:
                try:
                    target_m = int(str(schedule.deduction_month).strip())
                except (ValueError, TypeError):
                    pass
            return m == target_m

        return True
