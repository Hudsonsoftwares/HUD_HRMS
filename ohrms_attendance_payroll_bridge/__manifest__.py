# -*- coding: utf-8 -*-
{
    'name': 'OHRMS Attendance Payroll Bridge',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Connects real Attendance data to Payroll computation and flags discrepancies',
    'description': """
OHRMS Attendance Payroll Bridge
===============================
Connects real Attendance data to Payroll computation, and detects/flags
discrepancies between scheduled and actual worked hours — mirroring
Odoo's official Enterprise Payroll behavior.
    """,
    'author': 'Cybrosys Technologies, Hudson Softwares',
    'depends': ['hr_payroll_community', 'hr_attendance'],
    'data': [
        'views/hr_payslip_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
