# -*- coding: utf-8 -*-
import logging
from odoo import fields
from ..base import BaseStatutoryService

_logger = logging.getLogger(__name__)


class EPFWageCalculator(BaseStatutoryService):
    """Calculates Actual PF Wage and Statutory Contribution Wage Basis."""

    def __init__(self, env, localdict=None):
        super().__init__(env)
        self.localdict = localdict

    def get_actual_pf_wage(self, payslip):
        """Delegates actual PF wage calculation to payslip domain API."""
        _logger.info("===================================================")
        _logger.info("6. Wage Calculator: get_actual_pf_wage()")
        _logger.info("===================================================")
        _logger.info("[EPFWageCalculator] Called get_actual_pf_wage(payslip=%s)", payslip)
        result = payslip.hds_in_get_actual_pf_wage(localdict=self.localdict)
        _logger.info("[EPFWageCalculator] Returned get_actual_pf_wage -> %s", result)
        return result

    def get_pf_contribution_wage(self, payslip):
        """
        Determines the wage basis for PF contribution.
        Capped at Statutory PF Wage Ceiling (default ₹15,000) unless:
        - Employee is an International Worker (IW)
        - Contribution basis is set to 'actual_basic' or 'actual_pf_wage'
        """
        _logger.info("===================================================")
        _logger.info("6. Wage Calculator: get_pf_contribution_wage()")
        _logger.info("===================================================")
        _logger.info("[EPFWageCalculator] Called get_pf_contribution_wage(payslip=%s)", payslip)
        employee = payslip.employee_id
        actual_pf_wage = self.get_actual_pf_wage(payslip)

        if employee.hds_in_is_international_worker:
            _logger.info("[EPFWageCalculator] International Worker -> Wage: %s", actual_pf_wage)
            return actual_pf_wage

        if employee.hds_in_pf_contribution_basis in ('actual_basic', 'actual_pf_wage'):
            _logger.info("[EPFWageCalculator] Basis '%s' -> Wage: %s", employee.hds_in_pf_contribution_basis, actual_pf_wage)
            return actual_pf_wage

        eval_date = payslip.date_to or fields.Date.today()
        pf_ceiling = self.get_pf_parameter('PF_WAGE_CEILING', date=eval_date)
        res = min(actual_pf_wage, pf_ceiling)
        _logger.info("[EPFWageCalculator] Capped Wage Basis (Ceiling: %s) -> %s", pf_ceiling, res)
        return res

