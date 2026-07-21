# -*- coding: utf-8 -*-
{
    'name': 'Hudson Dynamic Financial Report Views',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Interactive On-Screen Expandable Views for Financial Reports (Profit and Loss, Balance Sheet, Cash Flow)',
    'author': 'Antigravity',
    'depends': ['base_accounting_kit', 'web', 'account'],
    'data': [
        'views/financial_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hudson_dynamic_financial_view/static/src/css/dynamic_financial_report.css',
            'hudson_dynamic_financial_view/static/src/js/dynamic_financial_report.js',
            'hudson_dynamic_financial_view/static/src/xml/dynamic_financial_report.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
