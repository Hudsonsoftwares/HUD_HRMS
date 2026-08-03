# -*- coding: utf-8 -*-
{
    'name': 'Hudson Indian Final Settlement',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Employee Exit & Final Settlement Workflow for Hudson Indian Payroll',
    'author': 'Hudson Software Solutions',
    'depends': [
        'hr',
        'hr_payroll_community',
        'hudson_in_payroll',
        'hr_resignation',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/final_settlement_sequence.xml',
        'views/final_settlement_views.xml',
        'views/hr_resignation_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
