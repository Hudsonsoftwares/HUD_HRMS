# -*- coding: utf-8 -*-
{
    'name': 'OHRMS Overtime & Shortage Payroll Integration',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Calculates Overtime Pay and Shortage Deductions based on actual Attendance vs Scheduled Calendar hours.',
    'description': """
OHRMS Overtime & Shortage Payroll Integration
=============================================
This module integrates attendance-vs-schedule metrics directly into payroll:
- Computes actual vs scheduled hours.
- Automatically generates OVERTIME and SHORTAGE worked days lines.
- Adds Overtime Pay (OT) allowance and Shortage Deduction (SHORT) rules.
- Flags attendance discrepancies on payslips.
    """,
    'author': 'Hudson Softwares',
    'depends': ['hr_payroll_community', 'hr_attendance'],
    'data': [
        'data/hr_salary_rule_data.xml',
        'views/hr_version_views.xml',
        'views/hr_payslip_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
