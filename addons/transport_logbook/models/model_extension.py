from odoo import models, fields, api

class TransportLogbookEntryReport(models.AbstractModel):
    _name = 'report.transport_logbook.report_selected_logbook'
    _description = 'Selected Logbook Records Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        # When printing selected records, we'll use only the specific IDs passed
        report = self.env['ir.actions.report']._get_report_from_name('transport_logbook.report_selected_logbook')
        
        # Get the selected records only
        docs = self.env[report.model].browse(docids)
        
        # Sort records by date
        docs = docs.sorted(key=lambda r: r.date)
        
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': docs,
        }

class SimplyFleetVehicleDashboard(models.Model):
    _inherit = 'simply.fleet.vehicle'
    
    # Add computed fields for dashboard
    logbook_trip_count = fields.Integer(string='Total Trips', compute='_compute_logbook_stats')
    logbook_total_distance = fields.Float(string='Total Distance', compute='_compute_logbook_stats')
    logbook_entry_count = fields.Integer(string='Entry Count', compute='_compute_logbook_stats')
    
    @api.depends()
    def _compute_logbook_stats(self):
        for vehicle in self:
            entries = self.env['transport.logbook.entry'].search([('vehicle_id', '=', vehicle.id)])
            
            total_trips = 0
            total_distance = 0
            
            for entry in entries:
                if entry.vehicle_type == 'bus':
                    total_trips += entry.trip_number
                else:  # cab
                    total_trips += 1
                total_distance += entry.distance
            
            vehicle.logbook_trip_count = total_trips
            vehicle.logbook_total_distance = total_distance
            vehicle.logbook_entry_count = len(entries)
    
    def action_view_vehicle_logbook_from_dashboard(self):
        """Action to view logbook entries for this vehicle from dashboard"""
        self.ensure_one()
        
        # Determine vehicle type from entries or vehicle type
        entries = self.env['transport.logbook.entry'].search([('vehicle_id', '=', self.id)], limit=1)
        vehicle_type = entries.vehicle_type if entries else 'cab'
        
        return {
            'name': f'Logbook - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'transport.logbook.entry',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {
                'default_vehicle_id': self.id,
                'default_vehicle_type': vehicle_type,
                'search_default_vehicle_id': self.id,
            }
        }

class TransportVehicleDashboard(models.Model):
    _name = 'transport.vehicle.dashboard'
    _description = 'Transport Vehicle Dashboard'
    _auto = False
    
    vehicle_id = fields.Many2one('simply.fleet.vehicle', string='Vehicle', readonly=True)
    vehicle_name = fields.Char(string='Vehicle Name', readonly=True)
    total_trips = fields.Integer(string='Total Trips', readonly=True)
    total_distance = fields.Float(string='Total Distance', readonly=True)
    entry_count = fields.Integer(string='Entries', readonly=True)
    
    def init(self):
        """Create or replace the SQL view for dashboard"""
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW transport_vehicle_dashboard AS (
                SELECT 
                    MIN(l.id) as id,
                    l.vehicle_id as vehicle_id,
                    v.name as vehicle_name,
                    COUNT(DISTINCT l.id) as entry_count,
                    SUM(CASE 
                        WHEN l.vehicle_type = 'bus' THEN l.trip_number 
                        ELSE 1 
                    END) as total_trips,
                    SUM(l.distance) as total_distance
                FROM transport_logbook_entry l
                JOIN simply_fleet_vehicle v ON l.vehicle_id = v.id
                GROUP BY l.vehicle_id, v.name
            )
        """)
