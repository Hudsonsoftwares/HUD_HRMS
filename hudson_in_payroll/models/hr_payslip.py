# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def hds_in_get_actual_pf_wage(self, localdict=None):
        """
        Calculates the employee's actual PF-eligible wage for this payslip.

        Definition:
        Actual PF Wage = SUM of calculated amounts of salary rules where
                        hds_in_include_in_pf_wage = True.

        - Reusable by EPF, EPS, and EDLI calculation engines.
        - Configuration-driven: relies strictly on rule.hds_in_include_in_pf_wage.
        - Does NOT hard-code BASIC, DA, GROSS, or contract wage formulas.
        - Supports execution from both saved payslip line records and in-flight localdict execution
          during payslip compute_sheet evaluation.
        """
        self.ensure_one()
        pf_wage = 0.0

        # If called within in-flight payslip compute_sheet evaluation
        if localdict:
            rules_dict = {}
            if 'rules' in localdict and hasattr(localdict['rules'], 'dict'):
                rules_dict = localdict['rules'].dict
            elif 'rules' in localdict and isinstance(localdict['rules'], dict):
                rules_dict = localdict['rules']

            if rules_dict:
                rule_codes = list(rules_dict.keys())
                pf_rules = self.env['hr.salary.rule'].search([
                    ('code', 'in', rule_codes),
                    ('hds_in_include_in_pf_wage', '=', True)
                ])
                pf_rule_codes = set(pf_rules.mapped('code'))
                for code in pf_rule_codes:
                    rule_val = rules_dict.get(code)
                    if rule_val:
                        amt = getattr(rule_val, 'total', False)
                        if amt is False and isinstance(rule_val, dict):
                            amt = rule_val.get('total', 0.0)
                        if amt is False and isinstance(rule_val, (int, float)):
                            amt = float(rule_val)
                        pf_wage += (amt or 0.0)
                return pf_wage

        # Fallback to saved payslip lines on record
        for line in self.line_ids:
            if line.salary_rule_id.hds_in_include_in_pf_wage:
                pf_wage += line.total

        return pf_wage

    def get_pf_eligible_wage(self, localdict=None):
        """Alias for hds_in_get_actual_pf_wage for backwards compatibility."""
        return self.hds_in_get_actual_pf_wage(localdict=localdict)

    def hds_in_get_pf_contribution_wage(self, localdict=None):
        """
        Calculates the employee's PF Contribution Wage for this payslip.

        Definition:
        Phase 6 converts the Actual PF Wage into the statutory PF Contribution Wage based on
        employee configuration (hds_in_pf_contribution_basis) and statutory wage ceiling.

        - If contribution basis is 'actual_basic' or 'actual_pf_wage':
            returns Actual PF Wage (no ceiling applied).
        - If contribution basis is 'statutory_ceiling' or 'statutory_wage_ceiling':
            returns min(Actual PF Wage, Configured Statutory PF Wage Ceiling).
        - Statutory PF Wage Ceiling is retrieved via get_pf_parameter('PF_WAGE_CEILING')
          using payslip period date (date_to).
        - Reusable across all statutory PF calculation engines (Employee EPF, Employer EPF, EPS, EDLI).
        - Does NOT calculate any deductions or apply contribution rates.
        """
        self.ensure_one()
        actual_pf_wage = self.hds_in_get_actual_pf_wage(localdict=localdict)
        basis = self.employee_id.hds_in_pf_contribution_basis

        if basis in ('actual_basic', 'actual_pf_wage'):
            return actual_pf_wage

        eval_date = self.date_to or fields.Date.today()
        pf_ceiling = self.env['hr.rule.parameter'].get_pf_parameter('PF_WAGE_CEILING', date=eval_date)
        return min(actual_pf_wage, pf_ceiling)

    def get_pf_contribution_wage(self, localdict=None):
        """Alias for hds_in_get_pf_contribution_wage for backwards compatibility."""
        return self.hds_in_get_pf_contribution_wage(localdict=localdict)

