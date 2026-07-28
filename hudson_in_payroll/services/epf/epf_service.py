# -*- coding: utf-8 -*-
from ..audit.audit_service import StatutoryAuditSession
from .validator import EPFValidator
from .wage_calculator import EPFWageCalculator
from .employee_calculator import EPFEmployeeCalculator
from .pension_calculator import EPFPensionCalculator
from .employer_calculator import EPFEmployerCalculator


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

    def compute_employee_epf(self, payslip, localdict=None):
        ld = localdict if localdict is not None else self.localdict
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EPF') as audit:
            self.validator.validate_eligibility(payslip)
            actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip, localdict=ld)
            pf_wage = self.wage_calc.get_pf_contribution_wage(payslip, localdict=ld)
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

            # Delegate to EmployeeCalculator
            amount = self.employee_calc.compute(payslip, localdict=ld)
            audit.attach_output('employee_epf_deduction', amount)
            return amount

    def compute_employer_eps(self, payslip, localdict=None):
        ld = localdict if localdict is not None else self.localdict
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EPS') as audit:
            actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip, localdict=ld)
            eval_date = payslip.date_to or self.env.context.get('date')
            eps_rate = self.env['hr.rule.parameter'].get_pf_parameter('EPS_RATE', date=eval_date, as_decimal=False)
            eps_ceiling = self.env['hr.rule.parameter'].get_pf_parameter('EPS_WAGE_CEILING', date=eval_date)

            audit.attach_input('actual_pf_wage', actual_pf_wage)
            audit.attach_input('eps_applicable', payslip.employee_id.hds_in_eps_applicable if payslip.employee_id else False)
            audit.attach_input('higher_pension', payslip.employee_id.hds_in_higher_pension if payslip.employee_id else False)

            audit.attach_parameter('EPS_RATE', eps_rate)
            audit.attach_parameter('EPS_WAGE_CEILING', eps_ceiling)

            result = self.pension_calc.compute(payslip, localdict=ld)
            audit.attach_output('employer_eps', result)
            return result

    def compute_employer_epf(self, payslip, localdict=None):
        ld = localdict if localdict is not None else self.localdict
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EPF_ER') as audit:
            pf_wage = self.wage_calc.get_pf_contribution_wage(payslip, localdict=ld)
            eval_date = payslip.date_to or self.env.context.get('date')
            er_rate = self.env['hr.rule.parameter'].get_pf_parameter('EMPLOYER_EPF_RATE', date=eval_date, as_decimal=False)

            audit.attach_input('pf_contribution_wage', pf_wage)
            audit.attach_parameter('EMPLOYER_EPF_RATE', er_rate)

            result = self.employer_calc.compute_employer_epf(payslip, localdict=ld)
            audit.attach_output('employer_epf_share', result)
            return result

    def compute_employer_edli(self, payslip, localdict=None):
        ld = localdict if localdict is not None else self.localdict
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EDLI') as audit:
            actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip, localdict=ld)
            eval_date = payslip.date_to or self.env.context.get('date')
            edli_rate = self.env['hr.rule.parameter'].get_pf_parameter('EDLI_RATE', date=eval_date, as_decimal=False)
            edli_ceiling = self.env['hr.rule.parameter'].get_pf_parameter('EDLI_WAGE_CEILING', date=eval_date)

            audit.attach_input('actual_pf_wage', actual_pf_wage)
            audit.attach_parameter('EDLI_RATE', edli_rate)
            audit.attach_parameter('EDLI_WAGE_CEILING', edli_ceiling)

            result = self.employer_calc.compute_edli(payslip, localdict=ld)
            audit.attach_output('employer_edli', result)
            return result

    def compute_epf_admin(self, payslip, localdict=None):
        ld = localdict if localdict is not None else self.localdict
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EPF_ADMIN') as audit:
            pf_wage = self.wage_calc.get_pf_contribution_wage(payslip, localdict=ld)
            eval_date = payslip.date_to or self.env.context.get('date')
            admin_rate = self.env['hr.rule.parameter'].get_pf_parameter('EPF_ADMIN_RATE', date=eval_date, as_decimal=False)

            audit.attach_input('pf_contribution_wage', pf_wage)
            audit.attach_parameter('EPF_ADMIN_RATE', admin_rate)

            result = self.employer_calc.compute_epf_admin(payslip, localdict=ld)
            audit.attach_output('epf_admin_charges', result)
            return result

    def compute_edli_admin(self, payslip, localdict=None):
        ld = localdict if localdict is not None else self.localdict
        with StatutoryAuditSession(self.env, payslip, statutory_module='epf', rule_code='EDLI_ADMIN') as audit:
            actual_pf_wage = self.wage_calc.get_actual_pf_wage(payslip, localdict=ld)
            eval_date = payslip.date_to or self.env.context.get('date')
            admin_rate = self.env['hr.rule.parameter'].get_pf_parameter('EDLI_ADMIN_RATE', date=eval_date, as_decimal=False)

            audit.attach_input('actual_pf_wage', actual_pf_wage)
            audit.attach_parameter('EDLI_ADMIN_RATE', admin_rate)

            result = self.employer_calc.compute_edli_admin(payslip, localdict=ld)
            audit.attach_output('edli_admin_charges', result)
            return result
