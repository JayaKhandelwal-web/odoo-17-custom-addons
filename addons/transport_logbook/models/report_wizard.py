from odoo import models, fields, api
from datetime import datetime

class LogbookReportWizard(models.TransientModel):
    _name = 'transport.logbook.report.wizard'
    _description = 'Logbook Report Wizard'
    
    company_id = fields.Many2one('transport.company', string='Company')
    vehicle_id = fields.Many2one('simply.fleet.vehicle', string='Vehicle')
    route = fields.Char(string='Route')
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    report_type = fields.Selection([
        ('bus', 'Bus Logbook'),
        ('cab', 'Cab Logbook'),
        ('company', 'Company Logbook')
    ], string='Report Type', default='bus', required=True)
    
    @api.onchange('start_date', 'end_date')
    def _onchange_dates(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            self.end_date = self.start_date
    
    def print_report(self):
        # Determine which entries to include
        domain = []
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        if self.vehicle_id:
            domain.append(('vehicle_id', '=', self.vehicle_id.id))
        if self.start_date:
            domain.append(('date', '>=', self.start_date))
        if self.end_date:
            domain.append(('date', '<=', self.end_date))
        
        # Get report type specific domain
        if self.report_type == 'bus':
            domain.append(('vehicle_type', '=', 'bus'))
        elif self.report_type == 'cab':
            domain.append(('vehicle_type', '=', 'cab'))
        
        entries = self.env['transport.logbook.entry'].search(domain)
        
        if not entries:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No entries found',
                    'message': 'No logbook entries match the selected criteria.',
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        # Format date range
        date_range = f"{self.start_date.strftime('%d/%m/%Y')} - {self.end_date.strftime('%d/%m/%Y')}"
        
        # Determine month if applicable
        month = None
        if self.start_date and self.end_date and self.start_date.month == self.end_date.month and self.start_date.year == self.end_date.year:
            month = self.start_date.strftime('%B %Y')
        
        # Create the context with all needed data
        context = {
            'report_type': self.report_type,  # CRITICAL: passing the report type
            'date_range': date_range,
            'company_name': self.company_id.name if self.company_id else 'All Companies',
            'vehicle_no': self.vehicle_id.name if self.vehicle_id else 'All Vehicles',
            'route': self.route or 'All Routes',
            'month': month or '',
        }
        
        # Use the appropriate report based on report_type
        report_name = ''
        if self.report_type == 'bus':
            report_name = 'transport_logbook.action_report_bus_logbook'
        elif self.report_type == 'cab':
            report_name = 'transport_logbook.action_report_cab_logbook'
        elif self.report_type == 'company':
            report_name = 'transport_logbook.action_report_company_logbook'
        else:
            report_name = 'transport_logbook.action_report_selected_logbook'
        
        # Pass both the entries and the context to the report
        return self.env.ref(report_name).with_context(**context).report_action(entries)
