from odoo import models, fields, api

class TransportCompany(models.Model):
    _name = 'transport.company'
    _description = 'Transport Company'
    
    name = fields.Char(string='Company Name', required=True)
    address = fields.Text(string='Address')
    
    # Relations
    logbook_entry_ids = fields.One2many('transport.logbook.entry', 'company_id', string='Logbook Entries')
    
    # Computed fields
    total_trips = fields.Integer(string='Total Trips', compute='_compute_statistics', store=False)
    total_distance = fields.Float(string='Total Distance (km)', compute='_compute_statistics', store=False)
    
    @api.depends('logbook_entry_ids', 'logbook_entry_ids.distance', 'logbook_entry_ids.trip_number', 'logbook_entry_ids.vehicle_type')
    def _compute_statistics(self):
        for company in self:
            bus_entries = company.logbook_entry_ids.filtered(lambda r: r.vehicle_type == 'bus')
            cab_entries = company.logbook_entry_ids.filtered(lambda r: r.vehicle_type == 'cab')
            
            # For bus entries, sum the trip numbers
            bus_trips = sum(bus_entries.mapped('trip_number'))
            # For cab entries, count the entries
            cab_trips = len(cab_entries)
            
            company.total_trips = bus_trips + cab_trips
            company.total_distance = sum(company.logbook_entry_ids.mapped('distance'))
