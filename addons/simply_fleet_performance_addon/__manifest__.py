# -*- coding: utf-8 -*-
{
    'name': 'Simply Fleet - Performance & Rewards',
    'version': '17.0.1.0.0',
    'category': 'Fleet',
    'summary': 'Driver Performance Tracking and Reward System for Simply Fleet',
    'sequence': 10,
    'description': """
        Driver Performance & Reward System
        ===================================
        
        This module extends Simply Fleet with comprehensive driver performance tracking
        and automated reward system.
        
        Key Features:
        -------------
        * Automatic weekly and monthly performance tracking
        * Multi-metric performance scoring (100-point scale)
        * Performance grades: Excellent, Good, Average, Below Average, Poor
        * Automatic reward points calculation
        * Monetary reward conversion
        * Performance dashboard with charts
        * Driver comparison tools
        * Top performers ranking
        * Historical performance analytics
        
        Performance Metrics:
        -------------------
        * Fuel efficiency (mileage in km/L)
        * Cost management (cost per km)
        * Driving consistency (variance analysis)
        * Activity level (number of trips)
        
        Reward System:
        --------------
        * Grade-based point allocation
        * Bonus points for exceptional performance
        * Configurable reward amounts
        * Weekly and monthly periods
        * Automatic calculation via cron jobs
        
        Visual Analytics:
        ----------------
        * Interactive performance dashboard
        * Line charts for trend analysis
        * Bar charts for driver comparison
        * Pivot tables for detailed analysis
        * Calendar view for period tracking
        * Mobile-responsive design
        
        Workflow:
        ---------
        1. System generates performance records automatically
        2. Manager reviews and calculates performance
        3. Approve performance records
        4. Mark as rewarded after payment
        
        Requirements:
        ------------
        * Simply Fleet module (base)
        * HR module (for driver management)
        * Active fuel logs with driver assignments
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'simply_fleet',  # Base Simply Fleet module
        'hr',           # For driver/employee management
        'mail',         # For chatter and notifications
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data files
        'data/performance_sequence.xml',
        'data/performance_cron.xml',
        
        # Views
        'views/driver_performance_views.xml',
    ],
    
    # Assets Configuration
    'assets': {
        'web.assets_backend': [
            'simply_fleet_performance_addon/static/src/css/performance_dashboard.css',
            'simply_fleet_performance_addon/static/src/js/performance_dashboard.js',
            'simply_fleet_performance_addon/static/src/xml/performance_dashboard_template.xml',
        ],
    },
    
    'demo': [],
    'installable': True,
    'application': False,  # This is an extension, not a standalone app
    'auto_install': False,
    'license': 'LGPL-3',
    
    # Additional metadata
    'images': ['static/description/icon.png'],
    'external_dependencies': {
        'python': [],
        'bin': [],
    },
    
    # Price and currency for Odoo Apps Store (optional)
    'price': 0.00,
    'currency': 'USD',
    
    # Support information
    'support': 'support@yourcompany.com',
    'maintainer': 'Your Company',
}
