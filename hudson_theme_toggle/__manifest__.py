# -*- coding: utf-8 -*-
{
    'name': 'Hudson Odoo Theme Toggle',
    'version': '1.0.0',
    'category': 'Theme',
    'summary': 'Adds a persistent Dark/Light Mode toggle to Odoo profile dropdown',
    'description': """
Hudson Odoo Theme Toggle
========================
Provides a lightweight, clean, and persistent Dark Mode / Light Mode toggle
inside the backend user profile menu for Odoo Community.
    """,
    'author': 'Hudson Technologies',
    'depends': ['web', 'base'],
    'data': [
        'views/webclient_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hudson_theme_toggle/static/src/user_menu/user_menu_theme.js',
            'hudson_theme_toggle/static/src/scss/dark_mode.scss',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
