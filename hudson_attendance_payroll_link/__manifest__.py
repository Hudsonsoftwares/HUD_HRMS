# -*- coding: utf-8 -*-
{
    'name': 'Hudson Attendance and Payroll Connection',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Connects biometric attendance, contract rates, leave deductions, and auto-regularization with payroll.',
    'description': """
This module connects biometric attendance anomalies, contract rates, unpaid leaves, and regularizations with payroll.
    """,
    'author': 'Hudson Softwares',
    'depends': [
        'hr_payroll_community',
        'hr_attendance',
        'hr_holidays',
        'hudson_biometric_attendance',
        'mail',
        'calendar',
        'ohrms_overtime_shortage_payroll',
        'hrms_dashboard',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/hr_version_views.xml',
        'views/ir_cron_data.xml',
        'data/hr_salary_rule_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
