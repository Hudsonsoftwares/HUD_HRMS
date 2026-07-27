# -*- coding: utf-8 -*-
{
    'name': 'Hudson HR Snapshot',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Freezes employee, contract, statutory, and attendance details upon payslip confirmation.',
    'description': """
Hudson HR Snapshot
==================
Captures a frozen audit snapshot of employee profile, employment contract, statutory PF parameters,
and attendance summary at the moment a payslip is confirmed. Historical payslips preserve period-accurate
data even after live employee or contract records are updated.
    """,
    'author': 'Hudson Softwares',
    'website': 'https://www.hudsonsoftwares.com',
    'depends': [
        'hr',
        'hr_payroll_community',
        'hudson_in_payroll',
        'ohrms_payroll_reports',
    ],
    'data': [
        'security/hds_hr_snapshot_security.xml',
        'security/ir.model.access.csv',
        'views/hds_hr_snapshot_views.xml',
        'views/hr_payslip_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
