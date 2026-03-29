# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TourPackage(models.Model):
    _name = 'tour.package'
    _description = 'Tour Package'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Package Name', required=True, tracking=True)
    code = fields.Char('Package Code', required=True)
    sequence = fields.Integer('Sequence', default=10)

    # Package Details
    destination_ids = fields.Many2many('tour.destination', string='Destinations')
    duration_days = fields.Integer('Duration (Days)', required=True)
    duration_nights = fields.Integer('Duration (Nights)', required=True)

    # Pricing
    price_per_person = fields.Float('Price Per Person (Rs.)', required=True)
    child_price = fields.Float('Child Price (Rs.)')
    min_persons = fields.Integer('Minimum Persons', default=1)
    max_persons = fields.Integer('Maximum Persons', default=50)

    # Package Inclusions
    includes_accommodation = fields.Boolean('Includes Accommodation', default=True)
    includes_meals = fields.Boolean('Includes Meals', default=True)
    includes_transport = fields.Boolean('Includes Transport', default=True)
    includes_sightseeing = fields.Boolean('Includes Sightseeing', default=True)
    includes_guide = fields.Boolean('Includes Guide')

    # Package Details
    description = fields.Html('Description')
    itinerary = fields.Html('Itinerary')
    inclusions = fields.Html('Inclusions')
    exclusions = fields.Html('Exclusions')
    terms_conditions = fields.Html('Terms & Conditions')

    # Images
    image = fields.Binary('Main Image')
    images = fields.One2many('tour.package.image', 'package_id', 'Gallery Images')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive')
    ], string='Status', default='draft', tracking=True)

    # Website
    website_published = fields.Boolean('Published on Website', default=True)
    website_description = fields.Html('Website Description')

    # Booking Information
    booking_ids = fields.One2many('tour.booking', 'package_id', 'Bookings')
    booking_count = fields.Integer('Booking Count', compute='_compute_booking_count')

    # Availability
    available_from = fields.Date('Available From')
    available_to = fields.Date('Available To')

    active = fields.Boolean('Active', default=True)

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for package in self:
            package.booking_count = len(package.booking_ids)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_suspend(self):
        self.write({'state': 'suspended'})

    def action_view_bookings(self):
        return {
            'name': _('Tour Bookings'),
            'domain': [('package_id', '=', self.id)],
            'view_type': 'form',
            'res_model': 'tour.booking',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'context': {'default_package_id': self.id}
        }


class TourDestination(models.Model):
    _name = 'tour.destination'
    _description = 'Tour Destination'
    _order = 'name'

    name = fields.Char('Destination Name', required=True)
    code = fields.Char('Destination Code')
    state_id = fields.Many2one('res.country.state', 'State')
    country_id = fields.Many2one('res.country', 'Country', default=lambda self: self.env.ref('base.in'))
    description = fields.Text('Description')
    image = fields.Binary('Image')

    # Location Details
    latitude = fields.Float('Latitude')
    longitude = fields.Float('Longitude')

    # Tourist Information
    best_time_to_visit = fields.Char('Best Time to Visit')
    weather_info = fields.Text('Weather Information')
    local_language = fields.Char('Local Language')

    active = fields.Boolean('Active', default=True)


class TourPackageImage(models.Model):
    _name = 'tour.package.image'
    _description = 'Tour Package Images'

    name = fields.Char('Image Name')
    image = fields.Binary('Image', required=True)
    package_id = fields.Many2one('tour.package', 'Package', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)


class TourBooking(models.Model):
    _name = 'tour.booking'
    _description = 'Tour Booking'
    _order = 'booking_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Booking Reference', required=True, copy=False,
                       readonly=True, default=lambda self: _('New'))

    # Customer Information
    customer_id = fields.Many2one('res.partner', 'Customer', required=True)
    customer_name = fields.Char('Customer Name', required=True)
    customer_phone = fields.Char('Phone Number', required=True)
    customer_email = fields.Char('Email')

    # Tour Details
    package_id = fields.Many2one('tour.package', 'Tour Package', required=True, tracking=True)
    travel_date = fields.Date('Travel Date', required=True, tracking=True)
    return_date = fields.Date('Return Date', compute='_compute_return_date', store=True)

    # Passengers
    adults = fields.Integer('Adults', default=1, required=True)
    children = fields.Integer('Children', default=0)
    total_persons = fields.Integer('Total Persons', compute='_compute_total_persons', store=True)

    # Pricing
    adult_price = fields.Float('Adult Price', compute='_compute_prices', store=True)
    child_price = fields.Float('Child Price', compute='_compute_prices', store=True)
    subtotal = fields.Float('Subtotal', compute='_compute_amounts', store=True)
    discount = fields.Float('Discount')
    tax_amount = fields.Float('Tax Amount', compute='_compute_amounts', store=True)
    total_amount = fields.Float('Total Amount', compute='_compute_amounts', store=True)
    advance_amount = fields.Float('Advance Amount')
    balance_amount = fields.Float('Balance Amount', compute='_compute_balance', store=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    booking_date = fields.Datetime('Booking Date', default=fields.Datetime.now)
    special_requirements = fields.Text('Special Requirements')
    notes = fields.Text('Notes')

    active = fields.Boolean('Active', default=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tour.booking') or _('New')
        return super(TourBooking, self).create(vals)

    @api.depends('package_id', 'travel_date')
    def _compute_return_date(self):
        for booking in self:
            if booking.package_id and booking.travel_date:
                booking.return_date = fields.Date.add(booking.travel_date,
                                                      days=booking.package_id.duration_days - 1)
            else:
                booking.return_date = False

    @api.depends('adults', 'children')
    def _compute_total_persons(self):
        for booking in self:
            booking.total_persons = booking.adults + booking.children

    @api.depends('package_id', 'adults', 'children')
    def _compute_prices(self):
        for booking in self:
            booking.adult_price = booking.package_id.price_per_person
            booking.child_price = booking.package_id.child_price

    @api.depends('adults', 'children', 'adult_price', 'child_price', 'discount')
    def _compute_amounts(self):
        for booking in self:
            booking.subtotal = (booking.adults * booking.adult_price) + \
                               (booking.children * booking.child_price)
            booking.tax_amount = (booking.subtotal - booking.discount) * 0.18
            booking.total_amount = booking.subtotal - booking.discount + booking.tax_amount

    @api.depends('total_amount', 'advance_amount')
    def _compute_balance(self):
        for booking in self:
            booking.balance_amount = booking.total_amount - booking.advance_amount

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_start_tour(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})