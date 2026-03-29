# -*- coding: utf-8 -*-
{
    'name': 'Annapurna Travels',
    'version': '1.0.0',
    'category': 'Services/Travel',
    'summary': 'Complete Travel Management System for Bus Services, Tours & Events',
    'description': """
        Annapurna Travels - Luxurious Journey with Care
        ==============================================

        Comprehensive travel management solution for:
        * Luxury Bus Fleet Management
        * Corporate Travel Services
        * Marriage & Event Transportation
        * School Bus Services
        * Tour Package Management
        * Online Booking System
        * Customer Management
        * Website Integration

        Features:
        * Modern responsive website
        * Online booking system
        * Fleet management with different categories
        * Service type management
        * Customer testimonials
        * Route and pricing management
        * Booking tracking and management
    """,
    'author': 'Annapurna Travels',
    'website': 'https://annapurnatravels.co.in',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'website',
        'contacts',
        'mail',
        'portal',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Data
        'data/service_type_data.xml',
        'data/bus_category_data.xml',
        'data/website_data.xml',
        'data/bus_sample_data.xml',

        # Views (must be loaded before menus)
        'views/bus_fleet_views.xml',
        'views/booking_views.xml',
        'views/tour_package_views.xml',
        'views/service_type_views.xml',
        'views/customer_testimonial_views.xml',
        'views/client_logo_views.xml',  # Add this line

        # Menu (loaded after views to ensure actions exist)
        'views/menu_views.xml',

        # Website Templates
        'templates/website_layout.xml',
        'templates/homepage.xml',
        'templates/services.xml',
        'templates/fleet.xml',
        'templates/booking.xml',
        'templates/about.xml',
        'templates/contact.xml',
        'templates/tours.xml',
        'templates/bus_detail.xml',
        'templates/my_bookings.xml',
        'templates/clients_section.xml',  # Add this line in templates section
    ],
    'assets': {
        'web.assets_frontend': [
            'annapurna_travels/static/src/css/annapurna_style.css',
            'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css',
            'annapurna_travels/static/src/js/annapurna_main.js',
        ],
    },
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 1,
}