{
    'name': 'Interakt WhatsApp Integration',
    'version': '17.0.1.0.0',
    'category': 'Marketing/Communication',
    'summary': 'WhatsApp Business API Integration with Interakt',
    'description': """
        Interakt WhatsApp Integration
        =============================
        Send WhatsApp template messages through Interakt API

        Features:
        - Configure Interakt API credentials
        - Manage WhatsApp templates
        - Send template messages automatically on booking confirmation
        - Track message delivery status
        - View message history and logs
        - Support for dynamic template parameters
    """,
    'author': 'RAJA',
    'website': 'https://www.annapurnatravels.com',
    'depends': [
        'base',
        'mail',
        'fleet_booking',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/interakt_security.xml',
        'security/ir.model.access.csv',
        'data/interakt_template_data.xml',
        'views/interakt_config_views.xml',
        'views/interakt_template_views.xml',
        'views/interakt_message_log_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
