# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ServiceType(models.Model):
    _name = 'service.type'
    _description = 'Service Type'
    _order = 'sequence, name'

    name = fields.Char('Service Name', required=True)
    code = fields.Char('Service Code', required=True)
    sequence = fields.Integer('Sequence', default=10)
    description = fields.Text('Description')
    icon = fields.Char('Icon Class', help='CSS icon class for website display')
    image = fields.Binary('Service Image')

    # Pricing
    base_price = fields.Float('Base Price (Rs.)')
    price_per_km = fields.Float('Price Per KM (Rs.)')
    price_per_day = fields.Float('Price Per Day (Rs.)')

    # Service Features
    includes_driver = fields.Boolean('Includes Driver', default=True)
    includes_fuel = fields.Boolean('Includes Fuel', default=True)
    includes_toll = fields.Boolean('Includes Toll', default=False)
    includes_parking = fields.Boolean('Includes Parking', default=False)

    # Terms and Conditions
    terms_conditions = fields.Html('Terms & Conditions')
    cancellation_policy = fields.Html('Cancellation Policy')

    # Website Display
    website_published = fields.Boolean('Published on Website', default=True)
    website_description = fields.Html('Website Description')

    active = fields.Boolean('Active', default=True)

    # Relations
    booking_ids = fields.One2many('bus.booking', 'service_type_id', 'Bookings')
    booking_count = fields.Integer('Booking Count', compute='_compute_booking_count')

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for service in self:
            service.booking_count = len(service.booking_ids)

    def action_view_bookings(self):
        return {
            'name': _('Bookings'),
            'domain': [('service_type_id', '=', self.id)],
            'view_type': 'form',
            'res_model': 'bus.booking',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'context': {'default_service_type_id': self.id}
        }

    @api.model
    def get_website_services(self):
        """Return services for website display"""
        return self.search([('website_published', '=', True), ('active', '=', True)])