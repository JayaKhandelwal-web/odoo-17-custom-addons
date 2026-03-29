from odoo import models, api, fields
from datetime import datetime
from dateutil.relativedelta import relativedelta

class SimplyFleetDashboard(models.AbstractModel):
    _name = 'simply.fleet.dashboard'
    _description = 'Fleet Dashboard API'

    @api.model
    def get_dashboard_data(self, date_filter='this_month', vehicle_id=0):
        # 1. Date filtering logic
        today = fields.Date.today()
        if date_filter == 'this_month':
            start_date = today.replace(day=1)
            end_date = today + relativedelta(months=1, days=-1)
        elif date_filter == 'last_month':
            start_date = today + relativedelta(months=-1, day=1)
            end_date = start_date + relativedelta(months=1, days=-1)
        elif date_filter == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        else:
            start_date = today + relativedelta(years=-10)  # Fallback All Time
            end_date = today + relativedelta(years=10)

        domain = [('create_date', '>=', start_date), ('create_date', '<=', end_date)]
        fuel_domain = [('datetime', '>=', start_date), ('datetime', '<=', end_date)]
        wo_domain = [('date', '>=', start_date), ('date', '<=', end_date)]

        # 2. Fetch vehicle list for the dropdown filter
        all_active_vehicles = self.env['simply.fleet.vehicle'].search([('state', '=', 'active')])
        vehicle_list = [{'id': v.id, 'name': v.name} for v in all_active_vehicles]

        # 3. --- KPIs ---
        vehicle_count = len(all_active_vehicles)
        active_wo_count = self.env['simply.vehicle.work.order'].search_count(
            [('state', 'in', ['draft', 'confirmed', 'in_progress'])])

        tankers = self.env['simply.fleet.diesel.tanker'].search([])
        total_tanker_fuel = sum(tankers.mapped('current_fuel_level'))

        expiring_docs = self.env['simply.fleet.document'].search_count([('state', '=', 'expiring_soon')])

        # 4. --- Chart Data ---
        
        # Pie Chart: Vehicle Status Distribution
        vehicles = self.env['simply.fleet.vehicle'].read_group([], [], ['state'])
        vehicle_pie = {
            'labels': [v['state'] for v in vehicles],
            'data': [v['state_count'] for v in vehicles]
        }

        # --- TIMEZONE FIX FOR POSTGRESQL ---
        user_tz = self.env.context.get('tz') or 'UTC'
        if user_tz == 'Asia/Calcutta':
            user_tz = 'Asia/Kolkata'
        safe_env = self.env(context=dict(self.env.context, tz=user_tz))

        # Line Chart: Fuel Consumption over time (Grouped by month)
        fuel_logs = safe_env['simply.fleet.fuel.log'].read_group(fuel_domain, ['liters:sum'], ['datetime:month'])
        fuel_line = {
            'labels': [f['datetime:month'] for f in fuel_logs],
            'data': [f['liters'] for f in fuel_logs]
        }

        # Bar Chart: Work Order Costs
        work_orders = self.env['simply.vehicle.work.order'].read_group(wo_domain, ['total_cost:sum'], ['state'])
        wo_bar = {
            'labels': [w['state'] for w in work_orders],
            'data': [w['total_cost'] for w in work_orders]
        }

        # Column Chart: Tanker Capacity vs Current Level
        tanker_col = {
            'labels': tankers.mapped('name'),
            'capacity': tankers.mapped('capacity'),
            'current': tankers.mapped('current_fuel_level')
        }

        # 5. Mileage Line Chart (Dynamic based on Vehicle Filter)
        if vehicle_id:
            # Show historical mileage trend for ONE specific vehicle from its fuel logs
            specific_fuel_logs = self.env['simply.fleet.fuel.log'].search([
                ('vehicle_id', '=', int(vehicle_id)),
                ('datetime', '>=', start_date),
                ('datetime', '<=', end_date)
            ], order='datetime asc')
            
            # Filter logs that actually have mileage calculated
            valid_logs = specific_fuel_logs.filtered(lambda l: hasattr(l, 'mileage') and getattr(l, 'mileage', 0) > 0)
            
            mileage_line = {
                'labels': [log.datetime.strftime('%d %b %Y') for log in valid_logs] if valid_logs else ['No Data'],
                'data': [log.mileage for log in valid_logs] if valid_logs else [0],
                'label': 'Mileage Trend Over Time (km/l)'
            }
        else:
            # Fallback: Show comparison for ALL vehicles using the manual field
            mileage_line = {
                'labels': all_active_vehicles.mapped('name'),
                'data': all_active_vehicles.mapped('average_mileage'), 
                'label': 'Average Mileage Comparison (km/l)'
            }

        return {
            'kpis': {
                'active_vehicles': vehicle_count,
                'active_work_orders': active_wo_count,
                'total_tanker_fuel': round(total_tanker_fuel, 2),
                'expiring_docs': expiring_docs
            },
            'charts': {
                'vehicle_pie': vehicle_pie,
                'fuel_line': fuel_line,
                'wo_bar': wo_bar,
                'tanker_col': tanker_col,
                'mileage_line': mileage_line
            },
            'vehicles': vehicle_list
        }
