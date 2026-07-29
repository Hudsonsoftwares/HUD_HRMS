# -*- coding: utf-8 -*-
{
    'name': 'Hudson Attendance Timeline View',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Custom 24-Hour Day Timeline / Gantt-Style View for Odoo 19 Community Attendances',
    'description': """
Hudson Attendance Timeline View
================================
Provides a modern, interactive 24-hour horizontal timeline view for employee attendances:
- Left panel with employee avatars, names, daily worked hours, and expected hours progress bar.
- Right scrollable 24-hour grid panel (12 AM - 11 PM) with synchronized vertical scrolling.
- Real-time rendering of attendance bars with ongoing attendance pulsing indicators and anomaly highlights.
- Interactive drag-to-create with 5-minute snapping intervals.
- Click-to-add attendance opening standard Odoo FormViewDialog.
- Compatible with Light & Dark mode themes.
    """,
    'author': 'Hudson Softwares',
    'website': 'https://www.hudsonsoftwares.com',
    'license': 'LGPL-3',
    'depends': [
        'hr_attendance',
        'web',
    ],
    'data': [
        'views/attendance_timeline_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hudson_attendance_timeline/static/src/attendance_timeline/attendance_timeline.scss',
            'hudson_attendance_timeline/static/src/attendance_timeline/attendance_timeline.xml',
            'hudson_attendance_timeline/static/src/attendance_timeline/attendance_timeline.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
