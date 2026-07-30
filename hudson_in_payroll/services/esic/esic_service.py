# -*- coding: utf-8 -*-
import logging
from ..audit.audit_service import StatutoryAuditSession
from .validator import ESICValidator
from .wage_calculator import ESICWageCalculator
from .employee_calculator import ESICEmployeeCalculator
from .employer_calculator import ESICEmployerCalculator

_logger = logging.getLogger(__name__)


class ESICService:
    """
    Unified Pure Python Facade for ESIC Domain Services with Statutory Audit Integration.
    Instantiated by HrPayslip with `env` and optional `localdict`. Zero ORM inheritance overhead.
    Follows exact same architecture as EPFService.
    """

    def __init__(self, env, localdict=None):
        self.env = env
        self.localdict = localdict
        self.validator = ESICValidator(env)
        self.wage_calc = ESICWageCalculator(env, localdict=localdict, validator=self.validator)
        self.employee_calc = ESICEmployeeCalculator(env, self.wage_calc, self.validator)
        self.employer_calc = ESICEmployerCalculator(env, self.wage_calc, self.validator)

    def compute_esic_wage(self, payslip):
        _logger.info("--> [ESICService] compute_esic_wage(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='esic', rule_code='ESIC_WAGE') as audit:
            esic_wage = self.wage_calc.get_esic_contributable_wage(payslip)
            ceiling = self.wage_calc.get_applicable_ceiling(payslip)
            audit.attach_input('is_pwd', payslip.employee_id.hds_in_is_pwd if payslip.employee_id else False)
            audit.attach_parameter('APPLICABLE_ESIC_CEILING', ceiling)
            audit.attach_output('esic_wage', esic_wage)
            _logger.info("<-- [ESICService] compute_esic_wage -> %s", esic_wage)
            return esic_wage

    def compute_esic_employee(self, payslip):
        _logger.info("--> [ESICService] compute_esic_employee(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='esic', rule_code='ESIC_EE') as audit:
            esic_wage = self.wage_calc.get_esic_contributable_wage(payslip)
            eval_date = payslip.date_to or self.env.context.get('date')
            ee_rate = self.env['hr.rule.parameter'].get_parameter('hds_in_esic_employee_rate', date=eval_date, as_decimal=False)
            ceiling = self.wage_calc.get_applicable_ceiling(payslip)

            audit.attach_input('esic_wage', esic_wage)
            audit.attach_input('is_pwd', payslip.employee_id.hds_in_is_pwd if payslip.employee_id else False)
            audit.attach_parameter('ESIC_EE_RATE', ee_rate)
            audit.attach_parameter('APPLICABLE_ESIC_CEILING', ceiling)

            amount = self.employee_calc.compute(payslip)
            audit.attach_output('esic_employee_deduction', amount)
            _logger.info("<-- [ESICService] compute_esic_employee -> %s", amount)
            return amount

    def compute_esic_employer(self, payslip):
        _logger.info("--> [ESICService] compute_esic_employer(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='esic', rule_code='ESIC_ER') as audit:
            esic_wage = self.wage_calc.get_esic_contributable_wage(payslip)
            eval_date = payslip.date_to or self.env.context.get('date')
            er_rate = self.env['hr.rule.parameter'].get_parameter('hds_in_esic_employer_rate', date=eval_date, as_decimal=False)

            audit.attach_input('esic_wage', esic_wage)
            audit.attach_parameter('ESIC_ER_RATE', er_rate)

            amount = self.employer_calc.compute(payslip)
            audit.attach_output('esic_employer_contribution', amount)
            _logger.info("<-- [ESICService] compute_esic_employer -> %s", amount)
            return amount
