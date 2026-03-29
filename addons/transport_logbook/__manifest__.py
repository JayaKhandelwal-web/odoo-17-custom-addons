{
    'name': 'Transport Logbook',
    'version': '1.0',
    'summary': 'Manage transport logbooks for buses and cabs',
    'description': """
        Transport Logbook Module
        ========================
        This module allows you to keep track of your vehicle trips with a simple logbook.
        Features:
        - Track bus trips with Trip counts and Running KM
        - Track cab trips with Odometer readings and automated distance calculation
        - Manage companies with logbook statistics
        - Organize by company and vehicle
        - Filter by month, day, company, and vehicle
        - Print selected records directly
        - Export data as PDF
        - Auto-refresh forms with smart data prefilling
        - Enhanced user experience with Save & New functionality
        - Custom odometer widget for better UX
    """,
    'author': 'Annapurna Tour & Travels',
    'category': 'Services/Transport',
    'depends': ['base', 'simply_fleet'],
    'data': [
        # Security first
        'security/ir.model.access.csv',
        
        # Views first (no menus yet)
        'views/vehicle_views.xml',
        'views/logbook_views.xml',
        'views/company_views.xml',
        
        # Dashboard views 
        'views/vehicle_dashboard_views.xml',
        
        # Reports
        'report/logbook_report.xml',
        'report/clean_report_templates.xml',
        
        # Wizard views 
        'views/report_wizard_views.xml',
        
        # Menu should be absolutely last
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'transport_logbook/static/src/js/odometer_widget.js',
            'transport_logbook/static/src/js/vehicle_dashboard_action.js',
            'transport_logbook/static/src/js/logbook_form_widget.js',
            'transport_logbook/static/src/xml/odometer_templates.xml',
        ],
    },
    'images': ['static/description/icon.png'],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
