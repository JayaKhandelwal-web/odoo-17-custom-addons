from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class SimplyFleetTankerRefill(models.Model):
    _name = 'simply.fleet.tanker.refill'
    _description = 'Diesel Tanker Refill'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    
    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    tanker_id = fields.Many2one('simply.fleet.diesel.tanker', string='Tanker', required=True, ondelete='cascade')
    date = fields.Datetime(string='Refill Date', required=True, default=fields.Datetime.now)
    quantity_before_refill = fields.Float(string='Quantity Before Refill (Liters)', 
                                         readonly=True,
                                         help="Fuel level in the tanker before this refill")
    quantity = fields.Float(string='Refill Quantity (Liters)', required=True, help="Amount of fuel added in this refill")
    quantity_after_refill = fields.Float(string='Quantity After Refill (Liters)', compute='_compute_quantity_after_refill', store=True, help="Total fuel level after refill")
    vendor = fields.Char(string='Vendor')
    cost = fields.Float(string='Cost')
    notes = fields.Text(string='Notes')
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user.id, readonly=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    @api.onchange('tanker_id')
    def _onchange_tanker_id(self):
        """Update before quantity when tanker is selected (for form display only)"""
        if self.tanker_id:
            self.quantity_before_refill = self.tanker_id.current_fuel_level
        else:
            self.quantity_before_refill = 0.0

    @api.depends('quantity_before_refill', 'quantity')
    def _compute_quantity_after_refill(self):
        for record in self:
            record.quantity_after_refill = record.quantity_before_refill + record.quantity

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('simply.fleet.tanker.refill') or 'New'
                
            # Get the tanker and validate
            tanker = self.env['simply.fleet.diesel.tanker'].browse(vals.get('tanker_id'))
            if tanker:
                # Store the CURRENT fuel level as "before refill" (this is the key fix)
                current_level = tanker.current_fuel_level
                vals['quantity_before_refill'] = current_level
                
                quantity = vals.get('quantity', 0)
                
                # Check if adding this refill would exceed capacity
                new_level = current_level + quantity
                if new_level > tanker.capacity:
                    raise UserError(f"Cannot refill. The tanker capacity ({tanker.capacity} L) would be exceeded. Current level: {current_level} L, Trying to add: {quantity} L")
                
                # Update tanker's current fuel level to the NEW level
                tanker.write({
                    'current_fuel_level': new_level
                })
                
        return super().create(vals_list)
        
    def write(self, vals):
        """Handle updates to refill records"""
        for record in self:
            # If quantity is being changed after creation
            if 'quantity' in vals:
                old_quantity = record.quantity
                new_quantity = vals.get('quantity')
                quantity_difference = new_quantity - old_quantity
                
                if quantity_difference != 0:
                    tanker = record.tanker_id
                    new_total_level = record.quantity_before_refill + new_quantity
                    
                    # Check capacity
                    if new_total_level > tanker.capacity:
                        raise UserError(f"Cannot update refill. The tanker capacity ({tanker.capacity} L) would be exceeded.")
                    
                    # Update tanker fuel level by the difference
                    tanker.current_fuel_level += quantity_difference
                    
            # If tanker is being changed (should be rare but handle it)
            if 'tanker_id' in vals:
                old_tanker = record.tanker_id
                new_tanker = self.env['simply.fleet.diesel.tanker'].browse(vals.get('tanker_id'))
                
                if old_tanker and old_tanker != new_tanker:
                    # Return fuel to old tanker
                    old_tanker.current_fuel_level -= record.quantity
                    
                    # Store new "before refill" quantity
                    vals['quantity_before_refill'] = new_tanker.current_fuel_level
                    
                    # Check if new tanker can accommodate
                    new_total_level = new_tanker.current_fuel_level + record.quantity
                    if new_total_level > new_tanker.capacity:
                        raise UserError(f"Cannot change tanker. The new tanker capacity would be exceeded.")
                    
                    # Add fuel to new tanker
                    new_tanker.current_fuel_level += record.quantity
                    
        return super().write(vals)
        
    def unlink(self):
        """Handle deletion of refill records"""
        for record in self:
            if record.tanker_id:
                # Return the fuel back to tanker
                record.tanker_id.current_fuel_level -= record.quantity
        return super().unlink()
        
    def action_view_related_dispensing(self):
        """Show dispensing logs that occurred after this refill"""
        self.ensure_one()
        
        # Find next refill (if any)
        next_refill = self.env['simply.fleet.tanker.refill'].search([
            ('tanker_id', '=', self.tanker_id.id),
            ('date', '>', self.date)
        ], order='date asc', limit=1)
        
        # Create domain for dispensing logs
        domain = [
            ('tanker_id', '=', self.tanker_id.id),
            ('date', '>=', self.date)
        ]
        
        # If there's a next refill, only show dispensing logs up to that refill
        if next_refill:
            domain.append(('date', '<', next_refill.date))
            
        # Return action to view dispensing logs
        return {
            'name': f'Dispensing Logs After {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'simply.fleet.tanker.dispensing',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {'create': False},
            'target': 'current',
        }


class SimplyFleetTankerDispensing(models.Model):
    _name = 'simply.fleet.tanker.dispensing'
    _description = 'Diesel Tanker Dispensing'
    _order = 'date desc'
    
    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    tanker_id = fields.Many2one('simply.fleet.diesel.tanker', string='Tanker', required=True, ondelete='cascade')
    date = fields.Datetime(string='Dispensing Date', required=True, default=fields.Datetime.now)
    vehicle_id = fields.Many2one('simply.fleet.vehicle', string='Vehicle', required=True)
    quantity = fields.Float(string='Quantity (Liters)', required=True)
    odometer = fields.Float(string='Vehicle Odometer', required=True)
    notes = fields.Text(string='Notes')
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user.id, readonly=True)
    fuel_log_id = fields.Many2one('simply.fleet.fuel.log', string='Related Fuel Log', readonly=True)
    
    # Add related refill field to easily filter dispensing logs by refill
    related_refill_id = fields.Many2one('simply.fleet.tanker.refill', string='Related Refill', 
                                        compute='_compute_related_refill', store=True)
    
    @api.depends('tanker_id', 'date')
    def _compute_related_refill(self):
        """Determine which refill this dispensing is related to"""
        for record in self:
            # Find the most recent refill before this dispensing
            refill = self.env['simply.fleet.tanker.refill'].search([
                ('tanker_id', '=', record.tanker_id.id),
                ('date', '<=', record.date)
            ], order='date desc', limit=1)
            
            record.related_refill_id = refill.id if refill else False
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('simply.fleet.tanker.dispensing') or 'New'
                
            # Update the tanker's fuel level
            tanker = self.env['simply.fleet.diesel.tanker'].browse(vals.get('tanker_id'))
            quantity = vals.get('quantity', 0)
            
            if tanker:
                # Check if we have enough fuel
                if tanker.current_fuel_level < quantity:
                    raise UserError(f"Not enough fuel in tanker. Current level: {tanker.current_fuel_level} L")
                
                # Update tanker fuel level - this is now handled in the fuel_log create method
                # to avoid double reduction when created from a fuel log
                if not self.env.context.get('from_fuel_log'):
                    tanker.write({
                        'current_fuel_level': tanker.current_fuel_level - quantity
                    })
                
                # Create fuel log entry only if not created from a fuel log
                vehicle_id = vals.get('vehicle_id')
                if vehicle_id and not self.env.context.get('from_fuel_log'):
                    # Get previous odometer
                    vehicle = self.env['simply.fleet.vehicle'].browse(vehicle_id)
                    previous_log = self.env['simply.fleet.fuel.log'].search([
                        ('vehicle_id', '=', vehicle_id),
                        ('odometer', '!=', False)
                    ], order='datetime desc, id desc', limit=1)
                    
                    previous_odometer = previous_log.odometer if previous_log else vehicle.initial_odometer or 0.0
                    
                    # Create fuel log
                    fuel_log = self.env['simply.fleet.fuel.log'].with_context(from_dispensing=True).create({
                        'vehicle_id': vehicle_id,
                        'datetime': vals.get('date'),
                        'liters': quantity,
                        'odometer': vals.get('odometer'),
                        'previous_odometer': previous_odometer,
                        'price_per_liter': 0,  # Could be updated with actual price if needed
                        'total_amount': 0,      # Could be calculated based on price
                        'fuel_type': 'diesel',
                        'fill_type': 'full',
                        'station_type': 'diesel_tanker',
                        'notes': vals.get('notes', ''),
                        'diesel_tanker_id': tanker.id
                    })
                    
                    # Link fuel log to dispensing record
                    vals['fuel_log_id'] = fuel_log.id
                
        return super().create(vals_list)
    
    def write(self, vals):
        for record in self:
            # Handle quantity changes when not coming from fuel log
            if 'quantity' in vals and not self.env.context.get('from_fuel_log'):
                old_quantity = record.quantity
                new_quantity = vals.get('quantity')
                quantity_difference = new_quantity - old_quantity
                
                if quantity_difference != 0:
                    tanker = record.tanker_id
                    
                    # If increasing the amount (taking more fuel from tanker)
                    if quantity_difference > 0:
                        if tanker.current_fuel_level < quantity_difference:
                            raise UserError(f"Not enough fuel in tanker. Current level: {tanker.current_fuel_level} L, Additional needed: {quantity_difference} L")
                        tanker.current_fuel_level -= quantity_difference
                    # If decreasing the amount (returning fuel to tanker)
                    else:
                        tanker.current_fuel_level -= quantity_difference  # Negative difference means adding back
                        
                    # Update the related fuel log if it exists
                    if record.fuel_log_id:
                        record.fuel_log_id.with_context(from_dispensing=True).write({
                            'liters': new_quantity
                        })
                        
        return super().write(vals)
