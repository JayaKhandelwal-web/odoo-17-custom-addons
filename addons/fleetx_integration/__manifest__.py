# -*- coding: utf-8 -*-
{
    'name': 'FleetX Integration',
    'version': '17.0.1.0.0',
    'category': 'Vehicle Management',
    'summary': 'Integration with FleetX API for vehicle tracking and analytics',
    'description': """
FleetX Integration Module
=========================

This module provides integration with FleetX API for:
* Real-time vehicle tracking
* Fleet analytics and reporting
* Live vehicle status monitoring
* Fuel consumption tracking
* Location and route management

Key Features:
* Independent vehicle management system
* Real-time API synchronization
* Comprehensive dashboard
* Analytics and reporting
* Automated data sync
* Multi-company support
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/fleetx_data.xml',
        'data/ir_cron_data.xml',
        
        # Views (order matters - actions must be defined before menus that reference them)
        'views/fleetx_config_views.xml',
        'views/fleetx_vehicle_views.xml',
        'views/fleetx_analytics_views.xml',
        'views/res_config_settings_views.xml',
        'views/fleetx_menus.xml',  # Moved to last so all actions are defined
    ],
    'assets': {
        'web.assets_backend': [
            #'fleetx_integration/static/src/css/fleetx_styles.css',
            'fleetx_integration/static/src/js/fleetx_dashboard.js',
        ],
    },
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
    'external_dependencies': {
        'python': ['requests'],
    },
}
