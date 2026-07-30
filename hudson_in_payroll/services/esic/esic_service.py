# -*- coding: utf-8 -*-
import logging
from ..audit.audit_service import StatutoryAuditSession
from .validator import ESICValidator
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
        self.employee_calc = ESICEmployeeCalculator(env, self.validator)
        self.employer_calc = ESICEmployerCalculator(env, self.validator)

    def _get_gross_wage(self, payslip=None):
        """Extracts gross wage from localdict categories, evaluated rule dict, or active contract wage."""
        ld = self.localdict or {}
        gross_wage = 0.0
        categories = ld.get('categories')
        if categories and hasattr(categories, 'GROSS'):
            gross_wage = float(getattr(categories, 'GROSS', 0.0) or 0.0)

        if gross_wage <= 0.0 and ld:
            # Sum evaluated numeric earning rule values in localdict
            for k, v in ld.items():
                if isinstance(v, (int, float)) and k not in ('result', 'result_qty', 'result_rate', 'NET', 'ESIC_EE', 'ESIC_ER', 'EPF_EE', 'EPF_ER', 'PT', 'LWF', 'ESIC_WAGE', 'PF_WAGE'):
                    gross_wage += float(v)

        if gross_wage <= 0.0:
            contract = ld.get('contract') or (payslip.contract_id if payslip else False)
            if not contract and payslip and getattr(payslip, 'employee_id', False):
                contracts = self.env['hr.version'].search([('employee_id', '=', payslip.employee_id.id)])
                contract = contracts[0] if contracts else False
            if contract and hasattr(contract, 'wage'):
                gross_wage = float(contract.wage or 0.0)

        return max(gross_wage, 0.0)

    def _get_esic_contributable_wage(self, payslip):
        """Single entry eligibility validation & gross wage resolution."""
        if not self.validator.is_esic_eligible(payslip):
            return 0.0
        return self._get_gross_wage(payslip)

    def compute_esic_wage(self, payslip):
        _logger.info("--> [ESICService] compute_esic_wage(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='esic', rule_code='ESIC_WAGE') as audit:
            esic_wage = self._get_esic_contributable_wage(payslip)
            ceiling = self.validator.get_applicable_ceiling(payslip)
            audit.attach_input('is_pwd', payslip.employee_id.hds_in_is_pwd if payslip.employee_id else False)
            audit.attach_parameter('APPLICABLE_ESIC_CEILING', ceiling)
            audit.attach_output('esic_wage', esic_wage)
            _logger.info("<-- [ESICService] compute_esic_wage -> %s", esic_wage)
            return esic_wage

    def compute_esic_employee(self, payslip):
        _logger.info("--> [ESICService] compute_esic_employee(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='esic', rule_code='ESIC_EE') as audit:
            esic_wage = self._get_esic_contributable_wage(payslip)
            eval_date = payslip.date_to or self.env.context.get('date')
            ee_rate = self.env['hr.rule.parameter'].get_parameter('hds_in_esic_employee_rate', date=eval_date, as_decimal=False)
            ceiling = self.validator.get_applicable_ceiling(payslip)

            audit.attach_input('esic_wage', esic_wage)
            audit.attach_input('is_pwd', payslip.employee_id.hds_in_is_pwd if payslip.employee_id else False)
            audit.attach_parameter('ESIC_EE_RATE', ee_rate)
            audit.attach_parameter('APPLICABLE_ESIC_CEILING', ceiling)

            amount = self.employee_calc.compute(payslip, esic_wage=esic_wage)
            audit.attach_output('esic_employee_deduction', amount)
            _logger.info("<-- [ESICService] compute_esic_employee -> %s", amount)
            return amount

    def compute_esic_employer(self, payslip):
        _logger.info("--> [ESICService] compute_esic_employer(payslip=%s)", payslip)
        with StatutoryAuditSession(self.env, payslip, statutory_module='esic', rule_code='ESIC_ER') as audit:
            esic_wage = self._get_esic_contributable_wage(payslip)
            eval_date = payslip.date_to or self.env.context.get('date')
            er_rate = self.env['hr.rule.parameter'].get_parameter('hds_in_esic_employer_rate', date=eval_date, as_decimal=False)

            audit.attach_input('esic_wage', esic_wage)
            audit.attach_parameter('ESIC_ER_RATE', er_rate)

            amount = self.employer_calc.compute(payslip, esic_wage=esic_wage)
            audit.attach_output('esic_employer_contribution', amount)
            _logger.info("<-- [ESICService] compute_esic_employer -> %s", amount)
            return amount
