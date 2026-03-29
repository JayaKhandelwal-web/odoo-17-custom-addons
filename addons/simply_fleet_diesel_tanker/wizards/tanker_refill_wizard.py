from odoo import models, fields, api
from odoo.exceptions import UserError

class SimplyFleetTankerRefillWizard(models.TransientModel):
    _name = 'simply.fleet.tanker.refill.wizard'
    _description = 'Diesel Tanker Refill Wizard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    tanker_id = fields.Many2one('simply.fleet.diesel.tanker', string='Tanker', required=True, readonly=True)
    quantity = fields.Float(string='Refill Quantity (Liters)', required=True)
    vendor = fields.Char(string='Vendor')
    cost = fields.Float(string='Cost')
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    notes = fields.Text(string='Notes')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    
    # Display fields for better visibility - all computed to show real-time values
    current_level = fields.Float(string='Current Level (Before Refill)', compute='_compute_tanker_info', readonly=True)
    capacity = fields.Float(string='Total Capacity', compute='_compute_tanker_info', readonly=True)
    new_level = fields.Float(string='Level After Refill', compute='_compute_new_level', readonly=True)
    available_space = fields.Float(string='Available Space', compute='_compute_tanker_info', readonly=True)
    fuel_percentage_before = fields.Float(string='Current Fuel %', compute='_compute_fuel_percentages', readonly=True)
    fuel_percentage_after = fields.Float(string='Fuel % After Refill', compute='_compute_fuel_percentages', readonly=True)
    
    @api.depends('tanker_id')
    def _compute_tanker_info(self):
        """Compute current tanker information"""
        for wizard in self:
            if wizard.tanker_id:
                wizard.current_level = wizard.tanker_id.current_fuel_level
                wizard.capacity = wizard.tanker_id.capacity
                wizard.available_space = wizard.capacity - wizard.current_level
            else:
                wizard.current_level = 0
                wizard.capacity = 0
                wizard.available_space = 0
    
    @api.depends('current_level', 'quantity')
    def _compute_new_level(self):
        for wizard in self:
            wizard.new_level = wizard.current_level + wizard.quantity
    
    @api.depends('current_level', 'new_level', 'capacity')
    def _compute_fuel_percentages(self):
        for wizard in self:
            if wizard.capacity > 0:
                wizard.fuel_percentage_before = (wizard.current_level / wizard.capacity) * 100
                wizard.fuel_percentage_after = (wizard.new_level / wizard.capacity) * 100
            else:
                wizard.fuel_percentage_before = 0
                wizard.fuel_percentage_after = 0
    
    @api.onchange('quantity')
    def _onchange_quantity(self):
        """Validate refill quantity"""
        if self.quantity > 0 and self.current_level + self.quantity > self.capacity:
            return {
                'warning': {
                    'title': 'Capacity Exceeded!',
                    'message': f'The refill quantity exceeds tanker capacity.\n'
                              f'Current Level: {self.current_level} L\n'
                              f'Available Space: {self.available_space} L\n'
                              f'Trying to add: {self.quantity} L'
                }
            }
    
    def action_refill(self):
        """Perform the refill operation"""
        self.ensure_one()
        
        # Final validation
        if self.new_level > self.capacity:
            raise UserError(f"Cannot refill. The tanker capacity ({self.capacity} L) would be exceeded.\n"
                           f"Current Level: {self.current_level} L\n"
                           f"Available Space: {self.available_space} L\n"
                           f"Trying to add: {self.quantity} L")
        
        if self.quantity <= 0:
            raise UserError("Refill quantity must be greater than zero.")
        
        # Create refill log
        refill = self.env['simply.fleet.tanker.refill'].create({
            'tanker_id': self.tanker_id.id,
            'date': self.date,
            'quantity': self.quantity,
            'vendor': self.vendor,
            'cost': self.cost,
            'notes': self.notes
        })
        
        # Link attachments to the created refill record
        if self.attachment_ids:
            for attachment in self.attachment_ids:
                attachment.write({
                    'res_model': 'simply.fleet.tanker.refill',
                    'res_id': refill.id,
                })
        
        return {
            'type': 'ir.actions.act_window_close'
        }


class SimplyFleetTankerDispensingWizard(models.TransientModel):
    _name = 'simply.fleet.tanker.dispensing.wizard'
    _description = 'Diesel Tanker Dispensing Wizard'
    
    tanker_id = fields.Many2one('simply.fleet.diesel.tanker', string='Tanker', required=True, readonly=True)
    vehicle_id = fields.Many2one('simply.fleet.vehicle', string='Vehicle', required=True)
    quantity = fields.Float(string='Quantity (Liters)', required=True)
    odometer = fields.Float(string='Vehicle Odometer', required=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    notes = fields.Text(string='Notes')
    
    current_level = fields.Float(related='tanker_id.current_fuel_level', string='Current Level')
    vehicle_last_odometer = fields.Float(string='Last Odometer Reading', compute='_compute_last_odometer')
    
    @api.depends('vehicle_id')
    def _compute_last_odometer(self):
        for wizard in self:
            if wizard.vehicle_id:
                last_log = self.env['simply.fleet.fuel.log'].search([
                    ('vehicle_id', '=', wizard.vehicle_id.id),
                    ('odometer', '!=', False)
                ], order='datetime desc, id desc', limit=1)
                
                if last_log:
                    wizard.vehicle_last_odometer = last_log.odometer
                else:
                    wizard.vehicle_last_odometer = wizard.vehicle_id.initial_odometer or 0.0
            else:
                wizard.vehicle_last_odometer = 0.0
    
    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.odometer = self.vehicle_last_odometer
    
    def action_dispense(self):
        """Perform the dispensing operation"""
        self.ensure_one()
        
        # Check fuel level
        if self.quantity > self.current_level:
            raise UserError(f"Not enough fuel in tanker. Current level: {self.current_level} L")
        
        # Create dispensing log - which will also create the fuel log
        self.env['simply.fleet.tanker.dispensing'].create({
            'tanker_id': self.tanker_id.id,
            'vehicle_id': self.vehicle_id.id,
            'date': self.date,
            'quantity': self.quantity,
            'odometer': self.odometer,
            'notes': self.notes
        })
        
        return {
            'type': 'ir.actions.act_window_close'
        }
