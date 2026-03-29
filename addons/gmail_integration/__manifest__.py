# -*- coding: utf-8 -*-
{
    'name': 'Gmail',
    'version': '17.0.2.0.0',  # Updated version for Option 1 implementation
    'category': 'Productivity',
    'summary': 'Gmail Integration with Shared OAuth, Multi-User Support, Send, Receive, Mass Mailing and Templates',
    'description': """
        Gmail Integration Module - Enhanced Multi-User Version
        ======================================================
        
        This module provides complete Gmail integration for Odoo with enhanced multi-user support:
        
        New Features (Option 1 - Shared OAuth App):
        -------------------------------------------
        * **Shared OAuth App**: Single OAuth configuration for all users
        * **Multi-User Support**: Each user can connect multiple Gmail accounts
        * **User Ownership**: Proper account ownership and access control
        * **Account Sharing**: Share Gmail accounts with selected users or company-wide
        * **Enhanced Security**: User isolation and permission-based access
        * **System Configuration**: Admin-friendly OAuth setup in Settings
        
        Existing Features:
        -----------------
        * Send and receive emails through Gmail API
        * Real-time email synchronization
        * Email templates with CC/BCC support
        * Mass mailing capabilities
        * Complete email data storage
        * Email threading and conversation management
        * Attachment handling
        * OAuth 2.0 authentication
        * Sync logging and error handling
        * Pub/Sub push notifications support
    """,
    'author': 'Your Company Name',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail', 
        'base_setup',  # Added for res.config.settings
        #'mass_mailing',
        #'contacts',
    ],
    'external_dependencies': {
        'python': [
            'google-auth',
            'google-auth-oauthlib', 
            'google-api-python-client',
            #'google-cloud-pubsub',
            #'google-cloud-core',        
            #'requests',                 
        ],
    },
    'data': [
        # Security
        'security/gmail_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/gmail_cron.xml',
        'data/gmail_data.xml',  # Uncommented - contains default templates and config
        
        # Views - Templates and OAuth (Foundation)
        'views/oauth_templates.xml',
        
        # Views - Core Models (Define views before menus reference them)
        'views/gmail_dashboard_views.xml',           # Load before menu
        'views/gmail_account_views.xml',             # Load before menu
        'views/gmail_account_switcher_views.xml',    # Load before menu
        'views/gmail_message_views.xml',             # Load before menu
        'views/gmail_send_mail_views.xml',           # Load before menu
        'views/gmail_template_views.xml',
        'views/gmail_mass_mail_views.xml',
        'views/gmail_alert_settings_views.xml',     # Load before menu (menu references this)
        'views/gmail_alert_handler_views.xml',      # Load before menu
        
        # Views - Menu Structure (Load AFTER all views it references)
        'views/gmail_menu_views.xml',
        
        # Views - Configuration (Can reference menu structure safely)
        'views/gmail_config_views.xml',
        'views/gmail_notification_settings_views.xml',
        
        # Views - Wizards (Load last)
        'views/gmail_oauth_wizard_views.xml',
        'views/gmail_account_share_wizard_views.xml',
    ],
    'demo': [],
    'images': [
        'static/description/icon.png',
    ],
    'assets': {
        'web.assets_backend': [
            # CSS Files
            'gmail_integration/static/src/css/gmail_style.css',              
            'gmail_integration/static/src/css/gmail_dashboard.css',          
            'gmail_integration/static/src/css/gmail_compose_wizard.css',
            'gmail_integration/static/src/css/gmail_shared_oauth.css',  # NEW
            'gmail_integration/static/src/css/gmail_account_switcher.css',  # NEW
            
            # JavaScript Files
            'gmail_integration/static/src/js/gmail_compose_wizard.js',    
            'gmail_integration/static/src/js/gmail_widgets.js',
            'gmail_integration/static/src/js/gmail_system_check.js',  # NEW
            'gmail_integration/static/src/js/gmail_account_switcher.js',  # NEW
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    
    # Version Information
    #'post_init_hook': 'post_init_hook',  # Optional: for data migration
    #'uninstall_hook': 'uninstall_hook',  # Optional: for cleanup
    
    # Dependencies and Compatibility
    'odoo_version': '17.0',
    'python_requires': '>=3.8',
    
    # Module Classification
    'sequence': 100,
    'website_category': 'Email & Marketing',
    
    # Support Information
    'support': 'support@yourcompany.com',
    'maintainer': 'Your Company Development Team',
    
    # Additional Metadata
    'contributors': [
        'Your Name <your.email@company.com>',
    ],
    
    # Price and Currency (if commercial)
    # 'price': 99.00,
    # 'currency': 'EUR',
}
