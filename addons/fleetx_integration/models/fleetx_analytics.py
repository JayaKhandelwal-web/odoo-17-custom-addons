# -*- coding: utf-8 -*-
import logging
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class FleetXAnalytics(models.Model):
    _name = 'fleetx.analytics'
    _description = 'FleetX Analytics'
    _order = 'create_date desc'
    _rec_name = 'create_date'

    # Basic Information
    config_id = fields.Many2one('fleetx.config', string='Configuration', required=True)
    company_id = fields.Many2one('res.company', string='Company', related='config_id.company_id', store=True)
    
    # Vehicle Statistics
    total_vehicles = fields.Integer(string='Total Vehicles', default=0)
    running_vehicles = fields.Integer(string='Running Vehicles', default=0)
    idle_vehicles = fields.Integer(string='Idle Vehicles', default=0)
    parked_vehicles = fields.Integer(string='Parked Vehicles', default=0)
    removed_vehicles = fields.Integer(string='Removed Vehicles', default=0)
    inshop_vehicles = fields.Integer(string='In Shop Vehicles', default=0)
    disconnected_vehicles = fields.Integer(string='Disconnected Vehicles', default=0)
    unreachable_vehicles = fields.Integer(string='Unreachable Vehicles', default=0)
    immobilised_vehicles = fields.Integer(string='Immobilised Vehicles', default=0)
    nopower_vehicles = fields.Integer(string='No Power Vehicles', default=0)
    standby_vehicles = fields.Integer(string='Standby Vehicles', default=0)
    battery_discharged_vehicles = fields.Integer(string='Battery Discharged Vehicles', default=0)
    
    # Performance Metrics
    utilization = fields.Float(string='Utilization %', default=0)
    alarms = fields.Integer(string='Alarms', default=0)
    dtc = fields.Integer(string='DTC', default=0)
    
    # Fuel Sensor Statistics
    fuel_sensor_disconnected = fields.Integer(string='Fuel Sensor Disconnected', default=0)
    fuel_sensor_stuck = fields.Integer(string='Fuel Sensor Stuck', default=0)
    fuel_sensor_working = fields.Integer(string='Fuel Sensor Working', default=0)
    fuel_sensor_uncalibrated = fields.Integer(string='Fuel Sensor Uncalibrated', default=0)
    
    # Additional Information
    timezone = fields.Char(string='Timezone', default='Asia/Kolkata')
    currency = fields.Char(string='Currency', default='INR')
    fleet_type = fields.Char(string='Fleet Type')
    expiry = fields.Integer(string='Expiry', default=0)
    
    # Computed Fields
    active_vehicles = fields.Integer(string='Active Vehicles', compute='_compute_active_vehicles', store=True)
    inactive_vehicles = fields.Integer(string='Inactive Vehicles', compute='_compute_inactive_vehicles', store=True)
    moving_vehicles = fields.Integer(string='Moving Vehicles', compute='_compute_moving_vehicles', store=True)
    fuel_sensor_efficiency = fields.Float(string='Fuel Sensor Efficiency %', compute='_compute_fuel_sensor_efficiency', store=True)

    @api.depends('running_vehicles', 'idle_vehicles')
    def _compute_active_vehicles(self):
        for record in self:
            record.active_vehicles = record.running_vehicles + record.idle_vehicles

    @api.depends('total_vehicles', 'active_vehicles')
    def _compute_inactive_vehicles(self):
        for record in self:
            record.inactive_vehicles = record.total_vehicles - record.active_vehicles

    @api.depends('running_vehicles')
    def _compute_moving_vehicles(self):
        for record in self:
            record.moving_vehicles = record.running_vehicles

    @api.depends('fuel_sensor_working', 'total_vehicles')
    def _compute_fuel_sensor_efficiency(self):
        for record in self:
            if record.total_vehicles > 0:
                record.fuel_sensor_efficiency = (record.fuel_sensor_working / record.total_vehicles) * 100
            else:
                record.fuel_sensor_efficiency = 0

    @api.model
    def create_analytics_record(self, data, config_id):
        """Create analytics record from FleetX API data"""
        try:
            values = {
                'config_id': config_id,
                'total_vehicles': data.get('totalVehicles', 0),
                'running_vehicles': data.get('runningVehicles', 0),
                'idle_vehicles': data.get('idleVehicles', 0),
                'parked_vehicles': data.get('parkedVehicles', 0),
                'removed_vehicles': data.get('removedVehicles', 0),
                'inshop_vehicles': data.get('inshopVehicles', 0),
                'disconnected_vehicles': data.get('disconnectedVehicles', 0),
                'unreachable_vehicles': data.get('unreachableVehicles', 0),
                'immobilised_vehicles': data.get('immobilisedVehicles', 0),
                'nopower_vehicles': data.get('nopowerVehicles', 0),
                'standby_vehicles': data.get('standbyVehicles', 0),
                'battery_discharged_vehicles': data.get('batteryDischargedVehicles', 0),
                'utilization': data.get('utilization', 0),
                'alarms': data.get('alarms', 0),
                'dtc': data.get('dtc', 0),
                'fuel_sensor_disconnected': data.get('fuelSensorDisconnected', 0),
                'fuel_sensor_stuck': data.get('fuelSensorStuck', 0),
                'fuel_sensor_working': data.get('fuelSensorWorking', 0),
                'fuel_sensor_uncalibrated': data.get('fuelSensorUncalibrated', 0),
                'timezone': data.get('timezone', 'Asia/Kolkata'),
                'currency': data.get('currency', 'INR'),
                'fleet_type': data.get('fleetType', ''),
                'expiry': data.get('expiry', 0),
            }
            
            analytics_record = self.create(values)
            _logger.info(f'Created analytics record for config {config_id}')
            return analytics_record
            
        except Exception as e:
            _logger.error(f'Error creating analytics record: {str(e)}')
            return False

    @api.model
    def get_latest_analytics(self, config_id=None):
        """Get latest analytics data"""
        domain = []
        if config_id:
            domain.append(('config_id', '=', config_id))
        
        latest_record = self.search(domain, limit=1, order='create_date desc')
        if latest_record:
            return {
                'total_vehicles': latest_record.total_vehicles,
                'running_vehicles': latest_record.running_vehicles,
                'idle_vehicles': latest_record.idle_vehicles,
                'parked_vehicles': latest_record.parked_vehicles,
                'unreachable_vehicles': latest_record.unreachable_vehicles,
                'utilization': latest_record.utilization,
                'fuel_sensor_working': latest_record.fuel_sensor_working,
                'fuel_sensor_efficiency': latest_record.fuel_sensor_efficiency,
                'active_vehicles': latest_record.active_vehicles,
                'inactive_vehicles': latest_record.inactive_vehicles,
                'alarms': latest_record.alarms,
                'create_date': latest_record.create_date,
            }
        return {}

    @api.model
    def get_analytics_chart_data(self, days=7, config_id=None):
        """Get analytics data for charts"""
        domain = [
            ('create_date', '>=', fields.Datetime.now() - fields.timedelta(days=days))
        ]
        if config_id:
            domain.append(('config_id', '=', config_id))
        
        records = self.search(domain, order='create_date asc')
        
        chart_data = {
            'labels': [],
            'running': [],
            'idle': [],
            'parked': [],
            'utilization': [],
        }
        
        for record in records:
            chart_data['labels'].append(record.create_date.strftime('%Y-%m-%d %H:%M'))
            chart_data['running'].append(record.running_vehicles)
            chart_data['idle'].append(record.idle_vehicles)
            chart_data['parked'].append(record.parked_vehicles)
            chart_data['utilization'].append(record.utilization)
        
        return chart_data

    @api.model
    def cleanup_old_analytics(self):
        """Cleanup old analytics records (called by cron)"""
        try:
            # Keep only last 30 days of analytics data
            cutoff_date = fields.Datetime.now() - relativedelta(days=30)
            old_records = self.search([('create_date', '<', cutoff_date)])
            count = len(old_records)
            old_records.unlink()
            _logger.info(f'Cleaned up {count} old analytics records')
        except Exception as e:
            _logger.error(f'Error cleaning up analytics records: {str(e)}')

    def action_view_vehicles(self):
        """Open vehicles list view"""
        self.ensure_one()
        return {
            'name': _('Vehicles'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleetx.vehicle',
            'view_mode': 'tree,form',
            'domain': [('config_id', '=', self.config_id.id)],
            'context': {'default_config_id': self.config_id.id},
        }