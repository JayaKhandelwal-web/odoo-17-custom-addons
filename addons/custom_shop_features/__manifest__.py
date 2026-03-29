# -*- coding: utf-8 -*-
{
    'name': 'Custom Shop Features',
    'version': '17.0.1.0.0',
    'summary': 'Hide Add to Cart button and add social sharing',
    'description': """
        This module hides the Add to Cart button on product pages and
        adds social sharing buttons for Facebook, WhatsApp, Twitter,
        LinkedIn, and Email.
    """,
    'category': 'Website',
    'author': 'Your Name',
    'website': '',
    'depends': ['website_sale'],
    'data': [
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
