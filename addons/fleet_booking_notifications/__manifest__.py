# -*- coding: utf-8 -*-
{
    'name': 'Fleet Booking - Journey Notifications',
    'version': '17.0.1.0.0',
    'category': 'Services/Fleet',
    'summary': 'Upcoming journey popup notifications when opening Fleet Booking',
    'description': """
        Fleet Booking Journey Notifications
        =====================================
        Automatically displays a beautiful popup notification showing upcoming
        journey details whenever the Fleet Booking application is opened.

        Features:
        - Auto popup on Fleet Booking app open (shown once per day per browser session)
        - Today / Tomorrow / This Week filter tabs with journey counts
        - Journey cards showing From → To route with dot-line visualization
        - Customer name, vehicle type, driver, date/time details
        - Color-coded status badges (Confirmed, Enquiry, Quotation, Follow Up)
        - Highlights today's journeys in green, tomorrow's in blue
        - "Not Assigned" driver shown in red for quick action
        - Responsive grid layout with smooth hover effects
        - Works with Odoo 17 clean URL routing and legacy hash routing
    """,
    'author': 'RAJA',
    'website': '',
    'depends': ['fleet_booking'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'fleet_booking_notifications/static/src/css/fleet_notification.css',
            'fleet_booking_notifications/static/src/xml/fleet_notification_dialog.xml',
            'fleet_booking_notifications/static/src/js/fleet_notification_dialog.js',
            'fleet_booking_notifications/static/src/js/fleet_notification_starter.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
