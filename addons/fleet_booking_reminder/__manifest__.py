# -*- coding: utf-8 -*-
{
    'name': 'Fleet Booking — Journey Reminder Emails',
    'version': '17.0.1.0.0',
    'summary': 'Automated 2-day & 1-day journey reminder emails for customers and fleet managers',
    'description': """
Fleet Booking Journey Reminder System
======================================
Sends automated reminder emails for confirmed fleet bookings:

**2 Days Before Journey**
- Customer: friendly preparation reminder with booking details & checklist
- Fleet Manager: internal ops brief with vehicle/driver/payment status & smart checklist

**1 Day Before Journey**
- Customer: final urgent reminder
- Fleet Manager: critical alert highlighting any ❌ action items (missing vehicle, driver, balance due)

Features
---------
- Daily cron job (08:00 AM IST / 02:30 UTC) fires all 4 emails automatically
- Anti-duplicate flags prevent customers from receiving repeated emails
- Manual re-send buttons on the booking form (manager buttons gated by security group)
- Reminder status banner on the form showing sent timestamps
- Full chatter logging for every email sent or failed
- Smart Jinja2 templates: vehicle/driver/payment status render as ✅ / ⚠️ / ❌
    """,
    'author': 'Raja — AlignTogether Solutions / Annapurna Tour & Travels',
    'website': 'https://aligntogether.in',
    'category': 'Fleet / Transport',
    'license': 'LGPL-3',

    'depends': [
        'fleet_booking',   # base fleet booking module (fleet.booking model)
        'mail',            # mail.template, message_post
    ],

    'data': [
        'data/fleet_booking_reminder_data.xml',
        'views/fleet_booking_reminder_views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
