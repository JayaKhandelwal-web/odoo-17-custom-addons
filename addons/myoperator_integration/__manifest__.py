{
    'name': 'MyOperator Integration',
    'version': '17.0.2.0.0',
    'summary': 'Complete MyOperator telephony and WhatsApp chat integration',
    'description': '''
        This module provides comprehensive integration with MyOperator services.

        Telephony Features:
        - Sync call logs from MyOperator
        - Manage MyOperator users
        - Click-to-call functionality
        - Callback functionality with advanced options
        - Webhook support for real-time call updates

        WhatsApp Chat Features:
        - WhatsApp Business API integration
        - Real-time chat conversations management
        - WhatsApp-like chat interface
        - Send text and template messages
        - Conversation assignment and status tracking
        - Message history and synchronization
        - Partner integration with chat history
        - Auto-reply functionality
        - Template message support for 24hr+ conversations

        General Features:
        - Partner phone number validation
        - Unified contact management
        - Webhook support for real-time updates
        - Comprehensive configuration management
    ''',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'category': 'Phone',
    'depends': ['base', 'contacts', 'crm', 'web'],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Data
        'data/cron_jobs.xml',

        # Menu Structure (must be loaded first)
        'views/menu_structure.xml',

        # Views - Configuration
        'views/myoperator_config_views.xml',
        'views/myoperator_chat_config_views.xml',

        # Views - Telephony
        'views/myoperator_call_log_views.xml',
        'views/myoperator_user_views.xml',

        # Views - Chat
        'views/myoperator_conversation_views.xml',

        # Views - Partner Extensions
        'views/res_partner_views.xml',

        'views/myoperator_dashboard_views.xml',
        'views/dashboard_config_wizard_views.xml',

        # Wizards
        'wizard/sync_call_logs_wizard.xml',
        'wizard/callback_wizard_view.xml',
        'wizard/send_message_wizard_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'myoperator_integration/static/src/js/phone_widget.js',
            #'myoperator_integration/static/src/js/chat_message_widget.js',
            'myoperator_integration/static/src/css/dashboard.css',
            'myoperator_integration/static/src/js/dashboard.js',
            'myoperator_integration/static/src/css/chat_interface.css',
            #'myoperator_integration/static/src/xml/chat_templates.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}