# -*- coding: utf-8 -*-
from odoo.tests import common


class TestPfWageBasis(common.TransactionCase):

    def setUp(self):
        super(TestPfWageBasis, self).setUp()
        self.SalaryRule = self.env['hr.salary.rule']
        self.Payslip = self.env['hr.payslip']
        self.PayslipLine = self.env['hr.payslip.line']
        self.Employee = self.env['hr.employee']
        self.Category = self.env['hr.salary.rule.category']

    def test_01_salary_rule_pf_wage_initial_flags(self):
        """Test initial configuration flags on standard salary rules."""
        basic_rule = self.env.ref('hr_payroll_community.hr_rule_basic', raise_if_not_found=False)
        if basic_rule:
            self.assertTrue(basic_rule.hds_in_include_in_pf_wage, "Basic Salary rule must be included in PF Wage by default.")

        da_rule = self.env.ref('hr_payroll_community.hr_rule_da', raise_if_not_found=False)
        if da_rule:
            self.assertTrue(da_rule.hds_in_include_in_pf_wage, "Dearness Allowance rule must be included in PF Wage by default.")

        hra_rule = self.env.ref('hr_payroll_community.hr_rule_hra', raise_if_not_found=False)
        if hra_rule:
            self.assertFalse(hra_rule.hds_in_include_in_pf_wage, "House Rent Allowance rule must NOT be included in PF Wage by default.")

    def test_02_configuration_driven_pf_wage_calculation(self):
        """Test that hds_in_get_actual_pf_wage dynamically calculates PF wage based on configuration flags."""
        category_alw = self.Category.search([], limit=1)
        
        # Create 3 custom salary rules
        rule_basic = self.SalaryRule.create({
            'name': 'Test Basic',
            'code': 'TEST_BASIC',
            'category_id': category_alw.id,
            'hds_in_include_in_pf_wage': True,
        })
        rule_da = self.SalaryRule.create({
            'name': 'Test DA',
            'code': 'TEST_DA',
            'category_id': category_alw.id,
            'hds_in_include_in_pf_wage': True,
        })
        rule_hra = self.SalaryRule.create({
            'name': 'Test HRA',
            'code': 'TEST_HRA',
            'category_id': category_alw.id,
            'hds_in_include_in_pf_wage': False,
        })

        employee = self.Employee.create({'name': 'PF Basis Test Employee'})
        payslip = self.Payslip.create({
            'name': 'Test Payslip',
            'employee_id': employee.id,
        })

        # Add lines to payslip
        self.PayslipLine.create({
            'slip_id': payslip.id,
            'salary_rule_id': rule_basic.id,
            'name': 'Test Basic',
            'code': 'TEST_BASIC',
            'category_id': category_alw.id,
            'amount': 20000.0,
            'quantity': 1.0,
            'rate': 100.0,
        })
        self.PayslipLine.create({
            'slip_id': payslip.id,
            'salary_rule_id': rule_da.id,
            'name': 'Test DA',
            'code': 'TEST_DA',
            'category_id': category_alw.id,
            'amount': 5000.0,
            'quantity': 1.0,
            'rate': 100.0,
        })
        self.PayslipLine.create({
            'slip_id': payslip.id,
            'salary_rule_id': rule_hra.id,
            'name': 'Test HRA',
            'code': 'TEST_HRA',
            'category_id': category_alw.id,
            'amount': 10000.0,
            'quantity': 1.0,
            'rate': 100.0,
        })

        # Calculation should sum only rules with hds_in_include_in_pf_wage=True (20,000 + 5,000 = 25,000)
        pf_wage = payslip.hds_in_get_actual_pf_wage()
        self.assertEqual(pf_wage, 25000.0, "PF eligible wage must equal 25000 (BASIC + DA).")

        # Dynamically toggle HRA to be included in PF Wage
        rule_hra.write({'hds_in_include_in_pf_wage': True})
        pf_wage_updated = payslip.hds_in_get_actual_pf_wage()
        self.assertEqual(pf_wage_updated, 35000.0, "PF eligible wage must update to 35000 after enabling HRA in configuration.")

    def test_03_in_flight_localdict_actual_pf_wage(self):
        """Test hds_in_get_actual_pf_wage during in-flight compute_sheet execution via localdict."""
        category_alw = self.Category.search([], limit=1)
        rule_basic = self.SalaryRule.create({
            'name': 'InFlight Basic',
            'code': 'INFLIGHT_BASIC',
            'category_id': category_alw.id,
            'hds_in_include_in_pf_wage': True,
        })
        rule_hra = self.SalaryRule.create({
            'name': 'InFlight HRA',
            'code': 'INFLIGHT_HRA',
            'category_id': category_alw.id,
            'hds_in_include_in_pf_wage': False,
        })

        employee = self.Employee.create({'name': 'InFlight Test Employee'})
        payslip = self.Payslip.create({'name': 'InFlight Payslip', 'employee_id': employee.id})

        simulated_localdict = {
            'rules': {
                'INFLIGHT_BASIC': {'total': 18000.0},
                'INFLIGHT_HRA': {'total': 7000.0},
            }
        }
        pf_wage_inflight = payslip.hds_in_get_actual_pf_wage(localdict=simulated_localdict)
        self.assertEqual(pf_wage_inflight, 18000.0, "In-flight PF wage should sum 18000 (only INFLIGHT_BASIC).")
