from odoo import models, fields, api


class VehicleExtension(models.Model):
    _inherit = 'simply.fleet.vehicle'

    booking_ids = fields.One2many(
        'fleet.booking',
        'vehicle_id',
        string='Bookings',
        help='Fleet bookings for this vehicle'
    )

    def action_view_bookings(self):
        self.ensure_one()
        return {
            'name': 'Vehicle Bookings',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'fleet.booking',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }