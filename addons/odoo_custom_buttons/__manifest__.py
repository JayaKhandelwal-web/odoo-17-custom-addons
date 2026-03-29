# -*- coding: utf-8 -*-
{
    'name': 'Universal Custom Big Buttons',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'summary': 'Add big custom action buttons (Save, Delete, Back) to all form views',
    'description': """
        Universal Custom Big Buttons for Odoo
        ======================================
        
        This module adds large, prominent action buttons to ALL form views in Odoo.
        
        Features:
        ---------
        * Big, easy-to-click buttons at the top of every form view
        * Save Button (Green)
        * Delete Button (Red)  
        * Back Button (Yellow)
        * Works on all existing modules and future modules automatically
        * Responsive design for mobile and tablet
        * Beautiful gradient colors with hover effects
        
        Position: Full width at the top of the form (Option 2)
        
        Compatible with: All Odoo modules (Sales, Inventory, HR, Accounting, Custom, etc.)
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'web',
    ],
    'data': [
        'views/form_view_examples.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_custom_buttons/static/src/css/custom_buttons.css',
            'odoo_custom_buttons/static/src/js/form_buttons.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
