from odoo import models, fields, api

class TransportVehicle(models.Model):
    _name = 'transport.vehicle'
    _description = 'Transport Vehicle'
    
    name = fields.Char(string='Vehicle Number', required=True)
    vehicle_type = fields.Selection([
        ('bus', 'Bus'),
        ('cab', 'Cab')
    ], string='Vehicle Type', required=True)
    
    # New field to link to SimplyFleet
    simply_fleet_vehicle_id = fields.Many2one('simply.fleet.vehicle', string='SimplyFleet Vehicle')
    
    logbook_entry_ids = fields.One2many('transport.logbook.entry', 'vehicle_id', string='Logbook Entries')
    driver_id = fields.Many2one('transport.driver', string='Current Driver')
    
    total_trips = fields.Integer(string='Total Trips', compute='_compute_statistics')
    total_distance = fields.Float(string='Total Distance (km)', compute='_compute_statistics')
    
    @api.depends('logbook_entry_ids', 'logbook_entry_ids.distance', 'logbook_entry_ids.trip_number', 'logbook_entry_ids.vehicle_type')
    def _compute_statistics(self):
        for vehicle in self:
            bus_entries = vehicle.logbook_entry_ids.filtered(lambda r: r.vehicle_type == 'bus')
            vehicle.total_trips = sum(bus_entries.mapped('trip_number')) + len(vehicle.logbook_entry_ids.filtered(lambda r: r.vehicle_type == 'cab'))
            vehicle.total_distance = sum(vehicle.logbook_entry_ids.mapped('distance'))
    
    # Method to sync with SimplyFleet vehicles
    @api.model
    def sync_from_simply_fleet(self):
        # Get all SimplyFleet vehicles
        simply_fleet_vehicles = self.env['simply.fleet.vehicle'].search([])
        
        for fleet_vehicle in simply_fleet_vehicles:
            # Determine vehicle type
            vehicle_type = 'cab'  # Default
            if fleet_vehicle.vehicle_type_id and (
                (fleet_vehicle.vehicle_type_id.name and 'bus' in fleet_vehicle.vehicle_type_id.name.lower()) or
                (fleet_vehicle.vehicle_type_id.code and 'bus' in fleet_vehicle.vehicle_type_id.code.lower())
            ):
                vehicle_type = 'bus'
            
            # Check if a transport vehicle already exists for this SimplyFleet vehicle
            transport_vehicle = self.search([('simply_fleet_vehicle_id', '=', fleet_vehicle.id)], limit=1)
            
            if transport_vehicle:
                # Update existing vehicle
                transport_vehicle.write({
                    'name': fleet_vehicle.name,
                    'vehicle_type': vehicle_type,
                })
            else:
                # Create new transport vehicle
                self.create({
                    'name': fleet_vehicle.name,
                    'vehicle_type': vehicle_type,
                    'simply_fleet_vehicle_id': fleet_vehicle.id,
                })
                
        return True
    
    def action_view_vehicle_logbook(self):
        self.ensure_one()
        return {
            'name': f'Logbook for {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'transport.logbook.entry',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id, 'default_vehicle_type': self.vehicle_type}
        }

# Extend SimplyFleet Vehicle model to add a reference to Transport Vehicle
class SimplyFleetVehicleExtension(models.Model):
    _inherit = 'simply.fleet.vehicle'
    
    transport_vehicle_id = fields.One2many('transport.vehicle', 'simply_fleet_vehicle_id', string='Transport Vehicle')
    
    # Add button to create/sync Transport Vehicle
    def action_create_transport_vehicle(self):
        self.ensure_one()
        
        # Determine vehicle type
        vehicle_type = 'cab'  # Default
        if self.vehicle_type_id and (
            (self.vehicle_type_id.name and 'bus' in self.vehicle_type_id.name.lower()) or
            (self.vehicle_type_id.code and 'bus' in self.vehicle_type_id.code.lower())
        ):
            vehicle_type = 'bus'
        
        # Check if a transport vehicle already exists
        transport_vehicle = self.env['transport.vehicle'].search([('simply_fleet_vehicle_id', '=', self.id)], limit=1)
        
        if transport_vehicle:
            # Update existing vehicle
            transport_vehicle.write({
                'name': self.name,
                'vehicle_type': vehicle_type,
            })
        else:
            # Create new transport vehicle
            self.env['transport.vehicle'].create({
                'name': self.name,
                'vehicle_type': vehicle_type,
                'simply_fleet_vehicle_id': self.id,
            })
            
        return True
