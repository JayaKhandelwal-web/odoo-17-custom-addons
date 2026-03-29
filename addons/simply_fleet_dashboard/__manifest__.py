{
    'name': 'Simply Fleet - Dashboard',
    'version': '17.0.1.0.0',
    'category': 'Fleet',
    'summary': 'Interactive OWL Dashboard for Simply Fleet & Diesel Tanker',
    'depends': ['base', 'web', 'simply_fleet', 'simply_fleet_diesel_tanker'],
    'data': [
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'simply_fleet_dashboard/static/src/xml/dashboard_template.xml',
            'simply_fleet_dashboard/static/src/js/dashboard_component.js',
            # We use standard Bootstrap/Odoo CSS, but you can add custom CSS here
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}