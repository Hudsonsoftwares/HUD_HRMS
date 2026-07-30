# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from ..services.esic.esic_service import ESICService


class TestESICService(TransactionCase):

    def setUp(self):
        super().setUp()
        self.employee = self.env['hr.employee'].create({
            'name': 'Test ESIC Employee',
            'hds_in_esic_applicable': True,
            'hds_in_is_pwd': False,
        })
        self.company = self.env.company
        self.company.hds_in_esic_applicable = True
        self.payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'date_from': '2026-04-01',
            'date_to': '2026-04-30',
        })

    def test_01_esic_calculation(self):
        """
        Gross Wage = ₹20,000 (<= ₹21,000 standard ceiling).
        ESIC EE Rate = 0.75% -> 20000 * 0.0075 = 150.0.
        ESIC ER Rate = 3.25% -> 20000 * 0.0325 = 650.0.
        """
        localdict = {'BASIC': 15000.0, 'HRA': 5000.0}
        service = ESICService(self.env, localdict=localdict)

        wage = service.compute_esic_wage(self.payslip)
        self.assertEqual(wage, 20000.0)

        ee_deduction = service.compute_esic_employee(self.payslip)
        self.assertEqual(ee_deduction, 150.0)

        er_contribution = service.compute_esic_employer(self.payslip)
        self.assertEqual(er_contribution, 650.0)

    def test_02_standard_ceiling_exceeded(self):
        """
        Gross Wage = ₹23,000 (> ₹21,000 standard ceiling).
        Non-PWD employee is not eligible. Returns 0.0.
        """
        localdict = {'BASIC': 18000.0, 'HRA': 5000.0}
        service = ESICService(self.env, localdict=localdict)

        wage = service.compute_esic_wage(self.payslip)
        self.assertEqual(wage, 0.0)

        ee_deduction = service.compute_esic_employee(self.payslip)
        self.assertEqual(ee_deduction, 0.0)

    def test_03_pwd_ceiling_eligible(self):
        """
        Gross Wage = ₹23,000 (> ₹21,000 standard ceiling, but <= ₹25,000 PWD ceiling).
        PWD employee (hds_in_is_pwd = True) is eligible under PWD ceiling parameter.
        EE = 23000 * 0.0075 = 172.5 -> ceil = 173.0.
        ER = 23000 * 0.0325 = 747.5 -> ceil = 748.0.
        """
        self.employee.hds_in_is_pwd = True
        localdict = {'BASIC': 18000.0, 'HRA': 5000.0}
        service = ESICService(self.env, localdict=localdict)

        wage = service.compute_esic_wage(self.payslip)
        self.assertEqual(wage, 23000.0)

        ee_deduction = service.compute_esic_employee(self.payslip)
        self.assertEqual(ee_deduction, 173.0)

        er_contribution = service.compute_esic_employer(self.payslip)
        self.assertEqual(er_contribution, 748.0)

    def test_04_esic_not_applicable(self):
        """When ESIC is disabled on employee or company, calculations return 0.0."""
        self.employee.hds_in_esic_applicable = False
        localdict = {'BASIC': 20000.0}
        service = ESICService(self.env, localdict=localdict)

        self.assertEqual(service.compute_esic_wage(self.payslip), 0.0)
        self.assertEqual(service.compute_esic_employee(self.payslip), 0.0)
        self.assertEqual(service.compute_esic_employer(self.payslip), 0.0)
