from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class TransportLogbookEntry(models.Model):
    _name = 'transport.logbook.entry'
    _description = 'Transport Logbook Entry'
    _order = 'date desc, id desc'
    
    # Changed to reference simply.fleet.vehicle instead of transport.vehicle
    vehicle_id = fields.Many2one('simply.fleet.vehicle', string='Vehicle', required=True)
    vehicle_type = fields.Selection([
        ('bus', 'Bus'),
        ('cab', 'Cab')
    ], string='Vehicle Type', required=True)
    
    company_id = fields.Many2one('transport.company', string='Company', required=True)
    # REMOVED driver_id field completely
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    
    # Fields for bus logbook
    trip_number = fields.Integer(string='Trip', default=0, 
                                 help="Number of trips conducted")
    running_km = fields.Float(string='Running KM', default=0.0,
                              help="Running kilometers for the bus")
    
    # Changed from Boolean to Float
    extra_distance = fields.Float(string='Extra KMs Run?', default=0.0,
                             help="Additional distance traveled beyond running kilometers")
    
    day = fields.Char(string='Day', compute='_compute_day', store=True)
    
    # Fields for cab logbook
    start_odometer = fields.Float(string='Starting Odometer', default=0.0)
    end_odometer = fields.Float(string='Ending Odometer', default=0.0)
    
    # Common fields
    distance = fields.Float(string='Distance (km)', compute='_compute_distance', store=True)
    month = fields.Char(string='Month', compute='_compute_month', store=True)
    
    # For backward compatibility - keep old fields but make them computed
    pickup_location = fields.Char(string='Pickup Location', compute='_compute_legacy_fields', store=True)
    drop_location = fields.Char(string='Drop Location', compute='_compute_legacy_fields', store=True)
    
    # Day of week and week number fields
    day_of_week = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], string='Day of Week', compute='_compute_day_of_week', store=True)
    
    week_number = fields.Integer(string='Week Number', compute='_compute_week_number', store=True)
    
    @api.model
    def last_day_of_month(self, date):
        """Return the last day of the month for a given date."""
        last_day = date + relativedelta(months=1, day=1, days=-1)
        return last_day
    
    @api.depends('vehicle_type', 'start_odometer', 'end_odometer', 'trip_number', 'running_km')
    def _compute_legacy_fields(self):
        for record in self:
            if record.vehicle_type == 'bus':
                record.pickup_location = f"Bus Trip #{record.trip_number}" if record.trip_number else "Bus Trip"
                record.drop_location = f"Running KM: {record.running_km}" if record.running_km else "Running"
            elif record.vehicle_type == 'cab':
                record.pickup_location = f"Start: {record.start_odometer}" if record.start_odometer else "Start"
                record.drop_location = f"End: {record.end_odometer}" if record.end_odometer else "End"
            else:
                record.pickup_location = False
                record.drop_location = False
    
    @api.depends('date')
    def _compute_day(self):
        for record in self:
            if record.date:
                record.day = record.date.strftime('%A')
            else:
                record.day = False
    
    @api.depends('date')
    def _compute_month(self):
        for record in self:
            if record.date:
                record.month = record.date.strftime('%B %Y')
            else:
                record.month = False
                
    @api.depends('start_odometer', 'end_odometer', 'vehicle_type', 'running_km', 'trip_number', 'extra_distance')
    def _compute_distance(self):
        for record in self:
            if record.vehicle_type == 'cab' and record.start_odometer and record.end_odometer:
                if record.end_odometer >= record.start_odometer:
                    record.distance = record.end_odometer - record.start_odometer
                else:
                    record.distance = 0
            elif record.vehicle_type == 'bus':
                # Base distance is running_km multiplied by trip_number
                base_distance = record.running_km * record.trip_number
                
                # Add extra distance directly
                base_distance += record.extra_distance
                
                record.distance = base_distance
            else:
                record.distance = 0
    
    @api.onchange('vehicle_type')
    def _onchange_vehicle_type(self):
        # Clear fields based on vehicle type but DO NOT clear vehicle_id
        if self.vehicle_type == 'bus':
            self.start_odometer = 0
            self.end_odometer = 0
        elif self.vehicle_type == 'cab':
            self.trip_number = 0
            self.running_km = 0
            self.extra_distance = 0
    
    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if not self.vehicle_id:
            return
            
        # Determine vehicle type from SimplyFleet vehicle's type
        vtype = 'cab'  # Default type
        
        try:
            # Safely check for vehicle_type_id and its attributes
            if hasattr(self.vehicle_id, 'vehicle_type_id') and self.vehicle_id.vehicle_type_id:
                type_name = self.vehicle_id.vehicle_type_id.name or ''
                type_code = self.vehicle_id.vehicle_type_id.code or ''
                
                if ('bus' in type_name.lower()) or ('bus' in type_code.lower()):
                    vtype = 'bus'
        except Exception:
            # Fallback to default 'cab' if any exception occurs
            vtype = 'cab'
            
        # Set the vehicle type
        self.vehicle_type = vtype
            
        # Clear fields based on vehicle type
        if vtype == 'bus':
            self.start_odometer = 0
            self.end_odometer = 0
        elif vtype == 'cab':
            self.trip_number = 0
            self.running_km = 0
            self.extra_distance = 0
    
    @api.onchange('running_km', 'trip_number')
    def _onchange_running_trip(self):
        # This will update the distance field through the compute method
        pass
    
    @api.depends('date')
    def _compute_day_of_week(self):
        for record in self:
            if record.date:
                # Monday is 0 in Python's weekday() function
                record.day_of_week = str(record.date.weekday())
            else:
                record.day_of_week = False

    @api.depends('date')
    def _compute_week_number(self):
        for record in self:
            if record.date:
                record.week_number = record.date.isocalendar()[1]
            else:
                record.week_number = False
        
    def save_quick_entry(self):
        """Save the quick entry form and return to the dashboard"""
        return {
            'type': 'ir.actions.act_window_close',
        }

    @api.model
    def get_last_entry_data(self):
        """Get data from the last entry for auto-filling new entries"""
        last_entry = self.search([], order='date desc, id desc', limit=1)
        if last_entry:
            next_date = last_entry.date + timedelta(days=1)
            return {
                'vehicle_id': last_entry.vehicle_id.id,
                'vehicle_type': last_entry.vehicle_type,
                'company_id': last_entry.company_id.id,
                'date': next_date.strftime('%Y-%m-%d'),
                'trip_number': last_entry.trip_number if last_entry.vehicle_type == 'bus' else 0,
                'running_km': last_entry.running_km if last_entry.vehicle_type == 'bus' else 0.0,
                'extra_distance': 0.0,  # Always reset extra distance
                'start_odometer': last_entry.end_odometer if last_entry.vehicle_type == 'cab' else 0.0,  # Start from last end
                'end_odometer': 0.0,  # Always reset end odometer
            }
        return {}

    def action_save_and_new(self):
        """Save current entry and open a new one with pre-filled data"""
        # Get current entry data for next entry
        next_date = self.date + timedelta(days=1)
        
        # Prepare default values for new entry
        defaults = {
            'default_vehicle_id': self.vehicle_id.id,
            'default_vehicle_type': self.vehicle_type,
            'default_company_id': self.company_id.id,
            'default_date': next_date.strftime('%Y-%m-%d'),
        }
        
        # Add vehicle type specific defaults
        if self.vehicle_type == 'bus':
            defaults.update({
                'default_trip_number': self.trip_number,
                'default_running_km': self.running_km,
                'default_extra_distance': 0.0,
                'default_start_odometer': 0.0,
                'default_end_odometer': 0.0,
            })
        elif self.vehicle_type == 'cab':
            defaults.update({
                'default_trip_number': 0,
                'default_running_km': 0.0,
                'default_extra_distance': 0.0,
                'default_start_odometer': self.end_odometer,
                'default_end_odometer': 0.0,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'transport.logbook.entry',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': defaults
        }
