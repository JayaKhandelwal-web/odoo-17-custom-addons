# -*- coding: utf-8 -*-
{
    'name': 'Attendance Kanban View',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Adds a Kanban view to HR Attendance with color-coded status cards',
    'description': """
        This module adds a Kanban view to the HR Attendance module.
        Features:
        - Kanban cards grouped by employee
        - Color-coded cards: Red for missing checkout, Green for completed
        - Displays Check In, Check Out, Work Hours, and Overtime
        - Easy visual overview of attendance status
    """,
    'author': 'RAJA Kumar',
    'depends': ['hr_attendance'],
    'data': [
        'views/attendance_kanban_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'attendance_kanban/static/src/css/attendance_kanban.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
