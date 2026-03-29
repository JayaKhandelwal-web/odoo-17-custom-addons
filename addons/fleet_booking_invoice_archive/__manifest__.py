# -*- coding: utf-8 -*-
{
    'name': 'Fleet Booking Invoice Archive',
    'version': '17.0.1.0.0',
    'category': 'Fleet',
    'summary': 'Automatically save and archive booking invoices as PDFs at different stages',
    'description': """
        Fleet Booking Invoice Archive
        ==============================
        * Automatically generates and saves booking invoices as PDFs
        * Triggers on state changes: Quotation, Confirmed, Completed, etc.
        * Maintains complete history of all generated invoices
        * Easy tracking and management of invoice documents
        * Smart button integration with booking records
    """,
    'author': 'RAJA - Annapurna Tour & Travels',
    'website': 'https://www.annapurnatravels.com',
    'depends': ['fleet_booking', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/fleet_booking_invoice_document_views.xml',
        'views/fleet_booking_views_inherit.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}