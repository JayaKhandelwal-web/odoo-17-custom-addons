from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from babel.dates import format_date

class VehicleMonthlyLogbookReport(models.AbstractModel):
    _name = 'report.transport_logbook.vehicle_monthly_report'
    _description = 'Vehicle Monthly Logbook Report'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        # Get the vehicles
        vehicle_ids = self.env['transport.vehicle'].browse(docids)
        
        # Get the date range for the current month
        today = fields.Date.today()
        first_day = today.replace(day=1)
        last_day = (first_day + relativedelta(months=1, days=-1))
        
        # Generate data for each vehicle
        result = []
        for vehicle in vehicle_ids:
            # Get logbook entries for this vehicle in the current month
            entries = self.env['transport.logbook.entry'].search([
                ('vehicle_id', '=', vehicle.id),
                ('date', '>=', first_day),
                ('date', '<=', last_day)
            ])
            
            # Organize entries by day of week
            days_data = {
                '0': {'trips': 0, 'running_km': 0, 'distance': 0},
                '1': {'trips': 0, 'running_km': 0, 'distance': 0},
                '2': {'trips': 0, 'running_km': 0, 'distance': 0},
                '3': {'trips': 0, 'running_km': 0, 'distance': 0},
                '4': {'trips': 0, 'running_km': 0, 'distance': 0},
                '5': {'trips': 0, 'running_km': 0, 'distance': 0},
                '6': {'trips': 0, 'running_km': 0, 'distance': 0},
            }
            
            # Count trips and distance by day of week
            for entry in entries:
                day_key = entry.day_of_week
                if day_key in days_data:
                    if vehicle.vehicle_type == 'bus':
                        days_data[day_key]['trips'] += entry.trip_number
                        days_data[day_key]['running_km'] += entry.running_km
                    days_data[day_key]['distance'] += entry.distance
            
            # Prepare the vehicle data
            vehicle_data = {
                'vehicle': vehicle,
                'days': days_data,
                'total_trips': sum(day['trips'] for day in days_data.values()),
                'total_distance': sum(day['distance'] for day in days_data.values()),
            }
            
            result.append(vehicle_data)
        
        return {
            'docs': vehicle_ids,
            'vehicle_data': result,
            'month_name': format_date(today, format='MMMM yyyy'),
            'days_of_week': [
                {'key': '0', 'name': 'Monday'},
                {'key': '1', 'name': 'Tuesday'},
                {'key': '2', 'name': 'Wednesday'},
                {'key': '3', 'name': 'Thursday'},
                {'key': '4', 'name': 'Friday'},
                {'key': '5', 'name': 'Saturday'},
                {'key': '6', 'name': 'Sunday'},
            ]
        }
