# -*- coding: utf-8 -*-
import logging
from ..audit.audit_service import StatutoryAuditSession
from .validator import EPFValidator
from .wage_calculator import EPFWageCalculator
from .employee_calculator import EPFEmployeeCalculator
from .pension_calculator import EPFPensionCalculator
from .employer_calculator import EPFEmployerCalculator

_logger = logging.getLogger(__name__)


class EPFService:
    """
    Unified Pure Python Facade for EPF Domain Services with Statutory Audit Integration.
    Instantiated by HrPayslip with `env` and optional `localdict`. Zero ORM inheritance overhead.
    """

    def __init__(self, env, localdict=None):
        self.env = env
        self.localdict = localdict
        self.validator = EPFValidator(env)
        self.wage_calc = EPFWageCalculator(env, localdict=localdict)
        self.employee_calc = EPFEmployeeCalculator(env, self.wage_calc)
        self.pension_calc = EPFPensionCalculator(env, self.wage_calc)
        self.employer_calc = EPFEmployerCalculator(env, self.wage_calc, self.pension_calc)

    def compute_pf_wage(self, payslip):
        _logger.info("--> [EPFService] compute_pf_wage(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='PF_WAGE') as audit:
            pf_wage = self.wage_calc.get_pf_contribution_wage(payslip)
            audit.attach_output('pf_wage', pf_wage)
            _logger.info("<-- [EPFService] compute_pf_wage -> %s", pf_wage)
            return pf_wage

    def compute_employee_epf(self, payslip):
        _logger.info("--> [EPFService] compute_employee_epf(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EPF') as audit:
            self.validator.validate_eligibility(payslip)
            actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip)
            pf_wage = self.wage_calc.get_pf_contribution_wage(payslip)
            eval_date = payslip.date_to or self.env.context.get('date')
            epf_rate = self.env['hr.rule.parameter'].get_pf_parameter('EPF_RATE', date=eval_date, as_decimal=False)
            pf_ceiling = self.env['hr.rule.parameter'].get_pf_parameter('PF_WAGE_CEILING', date=eval_date)

            audit.attach_input('actual_pf_wage', actual_pf_wage)
            audit.attach_input('pf_contribution_wage', pf_wage)
            audit.attach_input('pf_contribution_basis', payslip.employee_id.hds_in_pf_contribution_basis if payslip.employee_id else False)
            audit.attach_input('is_international_worker', payslip.employee_id.hds_in_is_international_worker if payslip.employee_id else False)
            audit.attach_input('vpf_type', payslip.employee_id.hds_in_vpf_type if payslip.employee_id else False)

            audit.attach_parameter('EPF_RATE', epf_rate)
            audit.attach_parameter('PF_WAGE_CEILING', pf_ceiling)

            amount = self.employee_calc.compute(payslip)
            audit.attach_output('employee_epf_deduction', amount)
            _logger.info("<-- [EPFService] compute_employee_epf -> %s", amount)
            return amount

    def compute_employer_total_pf(self, payslip):
        _logger.info("--> [EPFService] compute_employer_total_pf(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EPF_ER_TOT') as audit:
            pf_wage = self.wage_calc.get_pf_contribution_wage(payslip)
            eval_date = payslip.date_to or self.env.context.get('date')
            er_rate = self.env['hr.rule.parameter'].get_pf_parameter('EMPLOYER_EPF_RATE', date=eval_date, as_decimal=False)

            audit.attach_input('pf_contribution_wage', pf_wage)
            audit.attach_parameter('EMPLOYER_EPF_RATE', er_rate)

            result = self.employer_calc.compute_employer_total_pf(payslip)
            audit.attach_output('employer_total_pf', result)
            _logger.info("<-- [EPFService] compute_employer_total_pf -> %s", result)
            return result

    def compute_employer_epf_share(self, payslip):
        _logger.info("--> [EPFService] compute_employer_epf_share(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EPF_ER') as audit:
            pf_wage = self.wage_calc.get_pf_contribution_wage(payslip)
            eval_date = payslip.date_to or self.env.context.get('date')
            er_rate = self.env['hr.rule.parameter'].get_pf_parameter('EMPLOYER_EPF_RATE', date=eval_date, as_decimal=False)

            audit.attach_input('pf_contribution_wage', pf_wage)
            audit.attach_parameter('EMPLOYER_EPF_RATE', er_rate)

            result = self.employer_calc.compute_employer_epf_share(payslip)
            audit.attach_output('employer_epf_share', result)
            _logger.info("<-- [EPFService] compute_employer_epf_share -> %s", result)
            return result

    def compute_employer_epf(self, payslip):
        """Backward compatible alias delegating to compute_employer_epf_share."""
        return self.compute_employer_epf_share(payslip)

    def compute_employer_eps(self, payslip):
        _logger.info("--> [EPFService] compute_employer_eps(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EPS') as audit:
            actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip)
            eval_date = payslip.date_to or self.env.context.get('date')
            eps_rate = self.env['hr.rule.parameter'].get_pf_parameter('EPS_RATE', date=eval_date, as_decimal=False)
            eps_ceiling = self.env['hr.rule.parameter'].get_pf_parameter('EPS_WAGE_CEILING', date=eval_date)

            audit.attach_input('actual_pf_wage', actual_pf_wage)
            audit.attach_input('eps_applicable', payslip.employee_id.hds_in_eps_applicable if payslip.employee_id else False)
            audit.attach_input('higher_pension', payslip.employee_id.hds_in_higher_pension if payslip.employee_id else False)

            audit.attach_parameter('EPS_RATE', eps_rate)
            audit.attach_parameter('EPS_WAGE_CEILING', eps_ceiling)

            result = self.pension_calc.compute(payslip)
            audit.attach_output('employer_eps', result)
            _logger.info("<-- [EPFService] compute_employer_eps -> %s", result)
            return result

    def compute_employer_edli(self, payslip):
        _logger.info("--> [EPFService] compute_employer_edli(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EDLI') as audit:
            actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip)
            eval_date = payslip.date_to or self.env.context.get('date')
            edli_rate = self.env['hr.rule.parameter'].get_pf_parameter('EDLI_RATE', date=eval_date, as_decimal=False)
            edli_ceiling = self.env['hr.rule.parameter'].get_pf_parameter('EDLI_WAGE_CEILING', date=eval_date)

            audit.attach_input('actual_pf_wage', actual_pf_wage)
            audit.attach_parameter('EDLI_RATE', edli_rate)
            audit.attach_parameter('EDLI_WAGE_CEILING', edli_ceiling)

            result = self.employer_calc.compute_edli(payslip)
            audit.attach_output('employer_edli', result)
            _logger.info("<-- [EPFService] compute_employer_edli -> %s", result)
            return result

    def compute_epf_admin(self, payslip):
        _logger.info("--> [EPFService] compute_epf_admin(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EPF_ADMIN') as audit:
            pf_wage = self.wage_calc.get_pf_contribution_wage(payslip)
            eval_date = payslip.date_to or self.env.context.get('date')
            admin_rate = self.env['hr.rule.parameter'].get_pf_parameter('EPF_ADMIN_RATE', date=eval_date, as_decimal=False)

            audit.attach_input('pf_contribution_wage', pf_wage)
            audit.attach_parameter('EPF_ADMIN_RATE', admin_rate)

            result = self.employer_calc.compute_epf_admin(payslip)
            audit.attach_output('epf_admin_charges', result)
            _logger.info("<-- [EPFService] compute_epf_admin -> %s", result)
            return result

    def compute_edli_admin(self, payslip):
        _logger.info("--> [EPFService] compute_edli_admin(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EDLI_ADMIN') as audit:
            actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip)
            eval_date = payslip.date_to or self.env.context.get('date')
            admin_rate = self.env['hr.rule.parameter'].get_pf_parameter('EDLI_ADMIN_RATE', date=eval_date, as_decimal=False)

            audit.attach_input('actual_pf_wage', actual_pf_wage)
            audit.attach_parameter('EDLI_ADMIN_RATE', admin_rate)

            result = self.employer_calc.compute_edli_admin(payslip)
            audit.attach_output('edli_admin_charges', result)
            _logger.info("<-- [EPFService] compute_edli_admin -> %s", result)
            return result

