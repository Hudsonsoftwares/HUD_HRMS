# -*- coding: utf-8 -*-
{
    'name': 'Hudson Indian Payroll',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Indian Statutory Payroll Localization for Hudson HRMS',
    'author': 'Hudson Software Solutions',
    'depends': [
        'hr',
        'hr_payroll_community',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_rule_parameters.xml',
        'data/hr_salary_rules.xml',
        'views/res_config_settings_views.xml',
        'views/hr_rule_parameter_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_payslip_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
