# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class BusBooking(models.Model):
    _name = 'bus.booking'
    _description = 'Bus Booking'
    _order = 'booking_date desc, name desc'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Booking Reference', required=True, copy=False,
                       readonly=True, default=lambda self: _('New'))

    # Customer Information
    customer_id = fields.Many2one('res.partner', 'Customer', required=True,
                                  tracking=True)
    customer_name = fields.Char('Customer Name', required=True)
    customer_phone = fields.Char('Phone Number', required=True)
    customer_email = fields.Char('Email')
    customer_address = fields.Text('Address')

    # Booking Details
    service_type_id = fields.Many2one('service.type', 'Service Type', required=True,
                                      tracking=True)
    bus_id = fields.Many2one('bus.fleet', 'Bus', required=True, tracking=True)

    # Journey Details
    pickup_location = fields.Char('Pickup Location', required=True)
    drop_location = fields.Char('Drop Location')
    pickup_date = fields.Datetime('Pickup Date & Time', required=True, tracking=True)
    return_date = fields.Datetime('Return Date & Time')
    is_round_trip = fields.Boolean('Round Trip')

    distance_km = fields.Float('Distance (KM)')
    duration_days = fields.Integer('Duration (Days)', compute='_compute_duration', store=True)

    # Passengers
    passenger_count = fields.Integer('Number of Passengers', required=True, default=1)
    passenger_details = fields.Text('Passenger Details')
    special_requirements = fields.Text('Special Requirements')

    # Pricing
    base_amount = fields.Float('Base Amount', compute='_compute_amounts', store=True)
    km_amount = fields.Float('KM Amount', compute='_compute_amounts', store=True)
    day_amount = fields.Float('Day Amount', compute='_compute_amounts', store=True)
    extra_charges = fields.Float('Extra Charges')
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
    ], string='Status', default='draft', required=True, tracking=True)

    # Dates
    booking_date = fields.Datetime('Booking Date', default=fields.Datetime.now,
                                   required=True, tracking=True)
    confirmation_date = fields.Datetime('Confirmation Date', readonly=True)
    completion_date = fields.Datetime('Completion Date', readonly=True)

    # Additional Information
    notes = fields.Text('Internal Notes')
    driver_notes = fields.Text('Driver Notes')
    cancellation_reason = fields.Text('Cancellation Reason')

    # Website Booking
    is_website_booking = fields.Boolean('Website Booking', default=False)

    active = fields.Boolean('Active', default=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('bus.booking') or _('New')
        return super(BusBooking, self).create(vals)

    @api.depends('pickup_date', 'return_date')
    def _compute_duration(self):
        for booking in self:
            if booking.pickup_date and booking.return_date:
                delta = booking.return_date - booking.pickup_date
                booking.duration_days = max(1, delta.days)
            elif booking.pickup_date:
                booking.duration_days = 1
            else:
                booking.duration_days = 0

    @api.depends('service_type_id', 'bus_id', 'distance_km', 'duration_days',
                 'extra_charges', 'discount')
    def _compute_amounts(self):
        for booking in self:
            # Base amount from service type
            booking.base_amount = booking.service_type_id.base_price or 0

            # KM based amount
            km_rate = booking.service_type_id.price_per_km or booking.bus_id.per_km_rate or 0
            booking.km_amount = booking.distance_km * km_rate

            # Day based amount
            day_rate = booking.service_type_id.price_per_day or booking.bus_id.daily_rate or 0
            booking.day_amount = booking.duration_days * day_rate

            # Subtotal
            subtotal = booking.base_amount + booking.km_amount + booking.day_amount + booking.extra_charges - booking.discount

            # Tax (18% GST)
            booking.tax_amount = subtotal * 0.18

            # Total
            booking.total_amount = subtotal + booking.tax_amount

    @api.depends('total_amount', 'advance_amount')
    def _compute_balance(self):
        for booking in self:
            booking.balance_amount = booking.total_amount - booking.advance_amount

    @api.constrains('passenger_count', 'bus_id')
    def _check_passenger_capacity(self):
        for booking in self:
            if booking.passenger_count > booking.bus_id.seating_capacity:
                raise ValidationError(
                    _('Number of passengers (%s) exceeds bus capacity (%s).') %
                    (booking.passenger_count, booking.bus_id.seating_capacity)
                )

    @api.constrains('pickup_date', 'return_date')
    def _check_dates(self):
        for booking in self:
            if booking.pickup_date and booking.pickup_date < fields.Datetime.now():
                raise ValidationError(_('Pickup date cannot be in the past.'))
            if booking.return_date and booking.pickup_date and booking.return_date <= booking.pickup_date:
                raise ValidationError(_('Return date must be after pickup date.'))

    def action_confirm(self):
        if self.state != 'draft':
            raise UserError(_('Only draft bookings can be confirmed.'))

        # Check bus availability
        conflicting_bookings = self.env['bus.booking'].search([
            ('bus_id', '=', self.bus_id.id),
            ('state', 'in', ['confirmed', 'in_progress']),
            ('pickup_date', '<=', self.return_date or self.pickup_date),
            ('return_date', '>=', self.pickup_date),
            ('id', '!=', self.id)
        ])

        if conflicting_bookings:
            raise UserError(_('Bus is not available for the selected dates.'))

        self.write({
            'state': 'confirmed',
            'confirmation_date': fields.Datetime.now()
        })

        # Update bus status
        self.bus_id.write({'state': 'booked'})

        # Send confirmation email
        self._send_confirmation_email()

    def action_start_journey(self):
        if self.state != 'confirmed':
            raise UserError(_('Only confirmed bookings can be started.'))
        self.write({'state': 'in_progress'})

    def action_complete(self):
        if self.state != 'in_progress':
            raise UserError(_('Only in-progress bookings can be completed.'))
        self.write({
            'state': 'completed',
            'completion_date': fields.Datetime.now()
        })

        # Update bus status to available
        self.bus_id.write({'state': 'available'})

    def action_cancel(self):
        if self.state == 'completed':
            raise UserError(_('Completed bookings cannot be cancelled.'))

        self.write({'state': 'cancelled'})

        # Update bus status to available
        if self.bus_id.state == 'booked':
            self.bus_id.write({'state': 'available'})

    def _send_confirmation_email(self):
        """Send booking confirmation email to customer"""
        template = self.env.ref('annapurna_travels.email_booking_confirmation',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    @api.model
    def get_available_buses(self, pickup_date, return_date=None):
        """Get available buses for given date range"""
        domain = [('state', '=', 'available')]

        if pickup_date:
            # Check for conflicting bookings
            conflicting_bookings = self.search([
                ('state', 'in', ['confirmed', 'in_progress']),
                ('pickup_date', '<=', return_date or pickup_date),
                ('return_date', '>=', pickup_date)
            ])

            booked_bus_ids = conflicting_bookings.mapped('bus_id.id')
            if booked_bus_ids:
                domain.append(('id', 'not in', booked_bus_ids))

        return self.env['bus.fleet'].search(domain)


class BookingPayment(models.Model):
    _name = 'booking.payment'
    _description = 'Booking Payment'
    _order = 'payment_date desc'

    booking_id = fields.Many2one('bus.booking', 'Booking', required=True,
                                 ondelete='cascade')
    amount = fields.Float('Amount', required=True)
    payment_date = fields.Date('Payment Date', required=True,
                               default=fields.Date.today)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('cheque', 'Cheque')
    ], string='Payment Method', required=True)

    reference = fields.Char('Reference/Transaction ID')
    notes = fields.Text('Notes')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')