# -*- coding: utf-8 -*-
{
    'name': 'Hudson Indian Payroll — Professional Tax (PT) Reporting Suite',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Complete Professional Tax (PT) statutory reporting, registers, slab utilization, override month analysis, and audit tools for Hudson HRMS',
    'description': """
Hudson Indian Payroll — Professional Tax (PT) Reporting Suite
=============================================================
Comprehensive Indian Professional Tax (PT) reporting suite for Hudson HRMS:
- Professional Tax Register & Employee PT Statement
- Monthly, State-wise, and Company-wise PT Summaries
- Salary Slab Utilization & Wage Range Analysis
- February Override Month Deduction Report (MH/KA)
- PT Exception & Compliance Audit Reports
- PT Payroll vs Ledger Reconciliation Report
- Salary Revision PT Impact Analysis
- Employee State Mapping Validation
- PT Liability Summary & Configuration Audit
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
        'security/ir.model.access.csv',
        'views/hds_pt_report_wizard_views.xml',
        'views/hds_pt_report_tile_views.xml',
        'data/hds_pt_report_tiles.xml',
        'views/pt_report_menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
