from odoo import models, fields, api


class SimplyFleetVehicleIntegration(models.Model):
    """
    Extension of Simply Fleet Vehicle model to add Fleet Booking integration
    This ensures the booking_ids field is properly defined and prevents KeyError
    """
    _inherit = 'simply.fleet.vehicle'

    # Fleet Booking Integration Fields
    booking_ids = fields.One2many(
        'fleet.booking',
        'vehicle_id',
        string='Fleet Bookings',
        help='Fleet bookings for this vehicle'
    )

    booking_count = fields.Integer(
        string='Booking Count',
        compute='_compute_booking_count'
    )

    current_booking_id = fields.Many2one(
        'fleet.booking',
        string='Current Booking',
        compute='_compute_current_booking',
        store=True
    )

    # Compute methods
    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for record in self:
            record.booking_count = len(record.booking_ids)

    @api.depends('booking_ids', 'booking_ids.state')
    def _compute_current_booking(self):
        for record in self:
            current_booking = record.booking_ids.filtered(
                lambda b: b.state == 'confirmed'
            )[:1]  # Get the first confirmed booking
            record.current_booking_id = current_booking.id if current_booking else False

    def action_view_fleet_bookings(self):
        """Action to view fleet bookings for this vehicle"""
        self.ensure_one()
        return {
            'name': 'Fleet Bookings',
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.booking',
            'view_mode': 'tree,form,kanban',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }


class SimplyFleetVehicleTypeIntegration(models.Model):
    """
    Extension of Simply Fleet Vehicle Type model to add Fleet Booking integration
    """
    _inherit = 'simply.fleet.vehicle.type'

    booking_count = fields.Integer(
        string='Total Bookings',
        compute='_compute_booking_count'
    )

    @api.depends('vehicle_count')
    def _compute_booking_count(self):
        for record in self:
            vehicles = self.env['simply.fleet.vehicle'].search([
                ('vehicle_type_id', '=', record.id)
            ])
            record.booking_count = sum(vehicle.booking_count for vehicle in vehicles)

    def action_view_fleet_bookings(self):
        """Action to view fleet bookings for vehicles of this type"""
        self.ensure_one()
        vehicle_ids = self.env['simply.fleet.vehicle'].search([
            ('vehicle_type_id', '=', self.id)
        ]).ids
        return {
            'name': f'Fleet Bookings - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.booking',
            'view_mode': 'tree,form,kanban',
            'domain': [('vehicle_id', 'in', vehicle_ids)],
            'context': {},
        }


class HrEmployeeFleetIntegration(models.Model):
    """
    Extension of HR Employee model to add Fleet Booking integration for drivers
    """
    _inherit = 'hr.employee'

    # Fleet Booking fields for driver assignments
    driver_booking_count = fields.Integer(
        string='Driver Bookings',
        compute='_compute_driver_booking_count'
    )

    assigned_vehicle_ids = fields.One2many(
        'simply.fleet.vehicle',
        'driver_id',
        string='Assigned Vehicles'
    )

    @api.depends_context('uid')
    def _compute_driver_booking_count(self):
        """Compute fleet booking count for this employee as driver"""
        for employee in self:
            bookings = self.env['fleet.booking'].search_count([
                ('driver_id', '=', employee.id)
            ])
            employee.driver_booking_count = bookings

    def action_view_driver_fleet_bookings(self):
        """Action to view fleet bookings where this employee is the driver"""
        self.ensure_one()
        return {
            'name': f'Fleet Bookings - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.booking',
            'view_mode': 'tree,form,kanban',
            'domain': [('driver_id', '=', self.id)],
            'context': {'default_driver_id': self.id},
        }