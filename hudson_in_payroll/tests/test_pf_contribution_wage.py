# -*- coding: utf-8 -*-
from odoo.tests import common
from odoo import fields


class TestPfContributionWage(common.TransactionCase):

    def setUp(self):
        super(TestPfContributionWage, self).setUp()
        self.SalaryRule = self.env['hr.salary.rule']
        self.Payslip = self.env['hr.payslip']
        self.PayslipLine = self.env['hr.payslip.line']
        self.Employee = self.env['hr.employee']
        self.Category = self.env['hr.salary.rule.category']
        self.RuleParameter = self.env['hr.rule.parameter']
        self.RuleParameterValue = self.env['hr.rule.parameter.value']

        self.category_alw = self.Category.search([], limit=1)

        # Create salary rule included in PF wage
        self.rule_basic = self.SalaryRule.create({
            'name': 'Test Basic',
            'code': 'BASIC',
            'category_id': self.category_alw.id,
            'hds_in_include_in_pf_wage': True,
        })

        # Ensure PF Wage Ceiling parameter exists
        self.pf_ceiling_param = self.RuleParameter.search([('code', '=', 'hds_in_pf_wage_ceiling')], limit=1)
        if not self.pf_ceiling_param:
            self.pf_ceiling_param = self.RuleParameter.create({
                'name': 'PF Wage Ceiling',
                'code': 'hds_in_pf_wage_ceiling',
                'category': 'ceiling',
            })
            self.RuleParameterValue.create({
                'parameter_id': self.pf_ceiling_param.id,
                'date_from': '2014-09-01',
                'parameter_value': '15000',
            })

    def _create_payslip_with_lines(self, employee, basic_amount, date_to='2026-04-30'):
        payslip = self.Payslip.create({
            'name': 'Test Payslip',
            'employee_id': employee.id,
            'date_from': '2026-04-01',
            'date_to': date_to,
        })
        if basic_amount > 0:
            self.PayslipLine.create({
                'slip_id': payslip.id,
                'salary_rule_id': self.rule_basic.id,
                'name': 'Test Basic',
                'code': 'BASIC',
                'category_id': self.category_alw.id,
                'amount': float(basic_amount),
                'quantity': 1.0,
                'rate': 100.0,
            })
        return payslip

    def test_use_case_1_actual_12k_statutory_ceiling(self):
        """Use Case 1: Actual PF Wage 12,000, Basis Statutory Ceiling (15,000) -> 12,000"""
        employee = self.Employee.create({
            'name': 'Employee 1',
            'hds_in_pf_contribution_basis': 'statutory_ceiling',
        })
        payslip = self._create_payslip_with_lines(employee, 12000.0)
        self.assertEqual(payslip.hds_in_get_actual_pf_wage(), 12000.0)
        self.assertEqual(payslip.hds_in_get_pf_contribution_wage(), 12000.0)

    def test_use_case_2_actual_20k_statutory_ceiling(self):
        """Use Case 2: Actual PF Wage 20,000, Basis Statutory Ceiling (15,000) -> 15,000"""
        employee = self.Employee.create({
            'name': 'Employee 2',
            'hds_in_pf_contribution_basis': 'statutory_ceiling',
        })
        payslip = self._create_payslip_with_lines(employee, 20000.0)
        self.assertEqual(payslip.hds_in_get_actual_pf_wage(), 20000.0)
        self.assertEqual(payslip.hds_in_get_pf_contribution_wage(), 15000.0)

    def test_use_case_3_actual_20k_actual_pf_wage_basis(self):
        """Use Case 3: Actual PF Wage 20,000, Basis Actual PF Wage -> 20,000"""
        employee = self.Employee.create({
            'name': 'Employee 3',
            'hds_in_pf_contribution_basis': 'actual_basic',
        })
        payslip = self._create_payslip_with_lines(employee, 20000.0)
        self.assertEqual(payslip.hds_in_get_actual_pf_wage(), 20000.0)
        self.assertEqual(payslip.hds_in_get_pf_contribution_wage(), 20000.0)

    def test_use_case_4_actual_15k_statutory_ceiling(self):
        """Use Case 4: Actual PF Wage 15,000, Basis Statutory Ceiling (15,000) -> 15,000"""
        employee = self.Employee.create({
            'name': 'Employee 4',
            'hds_in_pf_contribution_basis': 'statutory_ceiling',
        })
        payslip = self._create_payslip_with_lines(employee, 15000.0)
        self.assertEqual(payslip.hds_in_get_actual_pf_wage(), 15000.0)
        self.assertEqual(payslip.hds_in_get_pf_contribution_wage(), 15000.0)

    def test_use_case_5_actual_0_statutory_ceiling(self):
        """Use Case 5: Actual PF Wage 0, Basis Statutory Ceiling -> 0"""
        employee = self.Employee.create({
            'name': 'Employee 5',
            'hds_in_pf_contribution_basis': 'statutory_ceiling',
        })
        payslip = self._create_payslip_with_lines(employee, 0.0)
        self.assertEqual(payslip.hds_in_get_actual_pf_wage(), 0.0)
        self.assertEqual(payslip.hds_in_get_pf_contribution_wage(), 0.0)

    def test_use_case_6_epf_not_applicable(self):
        """Use Case 6: EPF Applicable False -> still safely returns PF Contribution Wage without suppressing or raising errors."""
        employee = self.Employee.create({
            'name': 'Employee 6',
            'hds_in_epf_applicable': False,
            'hds_in_pf_contribution_basis': 'statutory_ceiling',
        })
        payslip = self._create_payslip_with_lines(employee, 20000.0)
        self.assertEqual(payslip.hds_in_get_pf_contribution_wage(), 15000.0)

    def test_alias_method(self):
        """Test backwards compatibility alias get_pf_contribution_wage."""
        employee = self.Employee.create({
            'name': 'Employee Alias Test',
            'hds_in_pf_contribution_basis': 'statutory_ceiling',
        })
        payslip = self._create_payslip_with_lines(employee, 20000.0)
        self.assertEqual(payslip.get_pf_contribution_wage(), 15000.0)

    def test_inflight_localdict_execution(self):
        """Test hds_in_get_pf_contribution_wage with in-flight localdict execution."""
        employee = self.Employee.create({
            'name': 'Employee Localdict Test',
            'hds_in_pf_contribution_basis': 'statutory_ceiling',
        })
        payslip = self.Payslip.create({
            'name': 'Inflight Payslip',
            'employee_id': employee.id,
            'date_to': '2026-04-30',
        })

        class RuleValue:
            def __init__(self, total):
                self.total = total

        localdict = {
            'rules': {
                'BASIC': RuleValue(25000.0),
            }
        }
        res = payslip.hds_in_get_pf_contribution_wage(localdict=localdict)
        self.assertEqual(res, 15000.0)

        # Test with actual_basic contribution basis
        employee.hds_in_pf_contribution_basis = 'actual_basic'
        res_uncapped = payslip.hds_in_get_pf_contribution_wage(localdict=localdict)
        self.assertEqual(res_uncapped, 25000.0)
