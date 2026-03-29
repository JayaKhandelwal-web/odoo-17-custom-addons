# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class FleetXVehicle(models.Model):
    _name = 'fleetx.vehicle'
    _description = 'FleetX Vehicle'
    _rec_name = 'vehicle_number'
    _order = 'vehicle_number asc'

    # Basic Information
    vehicle_id = fields.Char(string='Vehicle ID', required=True, index=True)
    account_id = fields.Char(string='Account ID')
    group_id = fields.Char(string='Group ID')
    vehicle_number = fields.Char(string='Vehicle Number', required=True, index=True)
    vehicle_name = fields.Char(string='Vehicle Name')

    # Vehicle Details
    vehicle_make = fields.Char(string='Make')
    vehicle_model = fields.Char(string='Model')
    vehicle_year = fields.Integer(string='Year')
    fuel_type = fields.Char(string='Fuel Type')
    vehicle_type_value = fields.Char(string='Vehicle Type')

    # Driver Information
    driver_name = fields.Char(string='Driver Name')
    driver_id = fields.Char(string='Driver ID')
    secondary_driver_id = fields.Char(string='Secondary Driver ID')

    # Location & Status
    latitude = fields.Float(string='Latitude', digits=(10, 6))
    longitude = fields.Float(string='Longitude', digits=(10, 6))
    address = fields.Text(string='Address')
    speed = fields.Float(string='Speed (km/h)')
    status = fields.Char(string='Status')
    current_status = fields.Selection([
        ('RUNNING', 'Running'),
        ('IDLE', 'Idle'),
        ('PARKED', 'Parked'),
        ('REMOVED', 'Removed'),
        ('UNREACHABLE', 'Unreachable'),
        ('NO_POWER', 'No Power'),
        ('BATTERY_DISCHARGED', 'Battery Discharged'),
        ('INSHOP', 'In Shop'),
        ('DISCONNECTED', 'Disconnected'),
        ('IMMOBILISED', 'Immobilised'),
        ('STANDBY', 'Standby'),
    ], string='Current Status', index=True)

    # Fuel Information
    total_fuel_consumption = fields.Float(string='Total Fuel Consumption (L)')
    fuel_tank_capacity = fields.Float(string='Fuel Tank Capacity (L)')
    current_fuel = fields.Float(string='Current Fuel (L)')
    fuel_sensor_status = fields.Char(string='Fuel Sensor Status')
    mileage = fields.Float(string='Mileage (km/L)')

    # Odometer
    total_odometer = fields.Float(string='Total Odometer (km)')
    current_km = fields.Float(string='Current KM')
    trip_odometer = fields.Float(string='Trip Odometer (km)')

    # Timing
    last_updated_at = fields.Datetime(string='Last Updated At')
    last_status_time = fields.Datetime(string='Last Status Time')
    last_acc_on = fields.Datetime(string='Last Ignition On')
    duration_engine_on = fields.Integer(string='Duration Engine On (seconds)')

    # Device Information
    device_id = fields.Char(string='Device ID')
    device_type = fields.Char(string='Device Type')
    provider_code = fields.Char(string='Provider Code')

    # Technical Details
    other_attributes = fields.Json(string='Other Attributes')
    tag_ids_list = fields.Char(string='Tag IDs')

    # Relations
    config_id = fields.Many2one('fleetx.config', string='Configuration', required=True)
    company_id = fields.Many2one('res.company', string='Company', related='config_id.company_id', store=True)

    # Computed Fields
    fuel_percentage = fields.Float(string='Fuel %', compute='_compute_fuel_percentage', store=True)
    is_moving = fields.Boolean(string='Is Moving', compute='_compute_is_moving', store=True)
    location_link = fields.Char(string='Google Maps Link', compute='_compute_location_link')

    # Status Colors for UI
    status_color = fields.Char(string='Status Color', compute='_compute_status_color')

    _sql_constraints = [
        ('unique_vehicle_id_config', 'unique(vehicle_id, config_id)',
         'Vehicle ID must be unique per configuration!'),
        ('unique_vehicle_number_config', 'unique(vehicle_number, config_id)',
         'Vehicle number must be unique per configuration!'),
    ]

    @api.depends('current_fuel', 'fuel_tank_capacity')
    def _compute_fuel_percentage(self):
        for record in self:
            if record.fuel_tank_capacity and record.fuel_tank_capacity > 0:
                record.fuel_percentage = (record.current_fuel / record.fuel_tank_capacity) * 100
            else:
                record.fuel_percentage = 0

    @api.depends('speed')
    def _compute_is_moving(self):
        for record in self:
            record.is_moving = record.speed > 0

    @api.depends('latitude', 'longitude')
    def _compute_location_link(self):
        for record in self:
            if record.latitude and record.longitude:
                record.location_link = f"https://www.google.com/maps?q={record.latitude},{record.longitude}"
            else:
                record.location_link = False

    @api.depends('current_status')
    def _compute_status_color(self):
        color_map = {
            'RUNNING': '#28a745',  # Green
            'IDLE': '#ffc107',  # Yellow
            'PARKED': '#17a2b8',  # Blue
            'REMOVED': '#6c757d',  # Gray
            'UNREACHABLE': '#dc3545',  # Red
            'NO_POWER': '#dc3545',  # Red
            'BATTERY_DISCHARGED': '#fd7e14',  # Orange
            'INSHOP': '#6f42c1',  # Purple
            'DISCONNECTED': '#dc3545',  # Red
            'IMMOBILISED': '#dc3545',  # Red
            'STANDBY': '#20c997',  # Teal
        }
        for record in self:
            record.status_color = color_map.get(record.current_status, '#6c757d')

    @api.model
    def create_or_update_vehicle(self, vehicle_data, config_id):
        """Create or update vehicle from FleetX API data - FIXED VERSION"""
        try:
            # Log the raw vehicle data for debugging
            vehicle_number = vehicle_data.get('vehicleNumber', 'Unknown')
            _logger.info(f'Processing vehicle: {vehicle_number}')
            _logger.debug(f'Raw vehicle data: {json.dumps(vehicle_data, indent=2, default=str)}')

            # Extract vehicle ID safely
            vehicle_id = vehicle_data.get('vehicleId')
            if not vehicle_id:
                _logger.error(f'Missing vehicleId for vehicle: {vehicle_number}')
                return False

            vehicle_id = str(vehicle_id)

            if not vehicle_number:
                _logger.error(f'Missing vehicleNumber for vehicleId: {vehicle_id}')
                return False

            # Search for existing vehicle
            existing_vehicle = self.search([
                ('vehicle_id', '=', vehicle_id),
                ('config_id', '=', config_id)
            ], limit=1)

            # Parse other attributes safely
            other_attrs = vehicle_data.get('otherAttributes', {})
            if isinstance(other_attrs, str):
                try:
                    other_attrs = json.loads(other_attrs)
                except:
                    other_attrs = {}

            # Prepare vehicle values with all the fields from your test data
            values = {
                'vehicle_id': vehicle_id,
                'account_id': str(vehicle_data.get('accountId', '')),
                'group_id': str(vehicle_data.get('groupId', '')),
                'vehicle_number': vehicle_number,
                'vehicle_name': vehicle_data.get('vehicleName', ''),
                'vehicle_make': vehicle_data.get('vehicleMake', ''),
                'vehicle_model': vehicle_data.get('vehicleModel', ''),
                'fuel_type': vehicle_data.get('fuelType', ''),
                'vehicle_type_value': vehicle_data.get('vehicleTypeValue', ''),
                'driver_name': vehicle_data.get('driverName', ''),
                'device_id': vehicle_data.get('deviceId', ''),
                'provider_code': vehicle_data.get('providerCode', ''),
                'other_attributes': other_attrs,
                'config_id': config_id,
            }

            # Handle driver IDs safely
            if 'driverId' in vehicle_data:
                values['driver_id'] = str(vehicle_data['driverId']) if vehicle_data['driverId'] else ''

            if 'secondaryDriverId' in vehicle_data:
                values['secondary_driver_id'] = str(vehicle_data['secondaryDriverId']) if vehicle_data[
                    'secondaryDriverId'] else ''

            # Handle optional numeric fields safely
            def safe_int(value, default=None):
                try:
                    return int(value) if value is not None and value != '' else default
                except (ValueError, TypeError):
                    return default

            def safe_float(value, default=0.0):
                try:
                    return float(value) if value is not None and value != '' else default
                except (ValueError, TypeError):
                    return default

            # Vehicle year
            values['vehicle_year'] = safe_int(vehicle_data.get('vehicleYear'))

            # Location data
            values['latitude'] = safe_float(vehicle_data.get('latitude'))
            values['longitude'] = safe_float(vehicle_data.get('longitude'))
            values['speed'] = safe_float(vehicle_data.get('speed'))

            # Address handling - this is important for your requirement
            address = vehicle_data.get('address', '')
            if address and len(address) > 500:  # Truncate if too long
                address = address[:500]
            values['address'] = address

            # Status fields
            values['status'] = vehicle_data.get('status', '')
            values['current_status'] = vehicle_data.get('currentStatus', '')

            # Fuel and odometer data
            values['total_fuel_consumption'] = safe_float(vehicle_data.get('totalFuelConsumption'))
            values['total_odometer'] = safe_float(vehicle_data.get('totalOdometer'))
            values['current_km'] = safe_float(vehicle_data.get('currentKm'))
            values['mileage'] = safe_float(vehicle_data.get('mileage'))

            # Engine duration
            values['duration_engine_on'] = safe_int(vehicle_data.get('durationEngineOn'), 0)

            # Parse timestamps safely
            def safe_timestamp_convert(timestamp_ms):
                try:
                    if timestamp_ms and timestamp_ms > 0:
                        # Convert from milliseconds to datetime
                        return datetime.fromtimestamp(timestamp_ms / 1000)
                except (ValueError, TypeError, OSError) as e:
                    _logger.warning(f'Invalid timestamp {timestamp_ms}: {e}')
                return None

            values['last_updated_at'] = safe_timestamp_convert(vehicle_data.get('lastUpdatedAt'))
            values['last_status_time'] = safe_timestamp_convert(vehicle_data.get('lastStatusTime'))
            values['last_acc_on'] = safe_timestamp_convert(vehicle_data.get('lastAccOn'))

            # Handle fuel information from otherAttributes
            if other_attrs:
                # Current fuel from 'fuel' field in otherAttributes
                if 'fuel' in other_attrs:
                    fuel_str = str(other_attrs['fuel']).replace('L', '').strip()
                    values['current_fuel'] = safe_float(fuel_str)

                # Fuel tank capacity
                if 'fuelTankCapacity' in other_attrs:
                    values['fuel_tank_capacity'] = safe_float(other_attrs['fuelTankCapacity'])

                # Fuel sensor status
                if 'fuelSensorStatus' in other_attrs:
                    values['fuel_sensor_status'] = str(other_attrs['fuelSensorStatus'])[:100]  # Limit length

                # Trip odometer
                if 'tripOdometer' in other_attrs:
                    values['trip_odometer'] = safe_float(other_attrs['tripOdometer'])

                # Device type
                if 'deviceType' in other_attrs:
                    values['device_type'] = str(other_attrs['deviceType'])[:50]  # Limit length

            # Handle tag IDs
            tag_ids = vehicle_data.get('tagIds', [])
            if isinstance(tag_ids, list):
                values['tag_ids_list'] = ','.join(map(str, tag_ids))
            else:
                values['tag_ids_list'] = str(tag_ids) if tag_ids else ''

            # Log the values being used
            _logger.debug(f'Vehicle values for {vehicle_number}: {json.dumps(values, indent=2, default=str)}')

            # Create or update vehicle
            if existing_vehicle:
                _logger.info(f'Updating existing vehicle: {vehicle_number}')
                existing_vehicle.write(values)
                return existing_vehicle
            else:
                _logger.info(f'Creating new vehicle: {vehicle_number}')
                try:
                    new_vehicle = self.create(values)
                    _logger.info(f'Successfully created vehicle: {vehicle_number} with ID: {new_vehicle.id}')
                    return new_vehicle
                except Exception as create_error:
                    _logger.error(f'Failed to create vehicle {vehicle_number}: {create_error}')
                    # Try to create with minimal required fields only
                    minimal_values = {
                        'vehicle_id': vehicle_id,
                        'vehicle_number': vehicle_number,
                        'config_id': config_id,
                        'vehicle_name': values.get('vehicle_name', ''),
                        'address': values.get('address', ''),
                        'current_status': values.get('current_status', ''),
                    }
                    try:
                        new_vehicle = self.create(minimal_values)
                        _logger.info(f'Created vehicle with minimal data: {vehicle_number}')
                        return new_vehicle
                    except Exception as minimal_error:
                        _logger.error(f'Failed to create vehicle even with minimal data: {minimal_error}')
                        return False

        except Exception as e:
            _logger.error(f'Error creating/updating vehicle {vehicle_data.get("vehicleNumber", "Unknown")}: {str(e)}')
            _logger.error(f'Exception details: {type(e).__name__}: {e}')
            import traceback
            _logger.error(f'Traceback: {traceback.format_exc()}')
            return False

    def action_open_location(self):
        """Open location in Google Maps"""
        self.ensure_one()
        if self.location_link:
            return {
                'type': 'ir.actions.act_url',
                'url': self.location_link,
                'target': 'new',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Location'),
                    'message': _('No location data available for this vehicle.'),
                    'type': 'warning',
                }
            }

    def action_refresh_data(self):
        """Refresh vehicle data from FleetX API"""
        for record in self:
            record.config_id.sync_vehicles()

    @api.model
    def get_vehicle_statistics(self):
        """Get vehicle statistics for dashboard"""
        return {
            'total': self.search_count([]),
            'running': self.search_count([('current_status', '=', 'RUNNING')]),
            'idle': self.search_count([('current_status', '=', 'IDLE')]),
            'parked': self.search_count([('current_status', '=', 'PARKED')]),
            'unreachable': self.search_count([('current_status', '=', 'UNREACHABLE')]),
            'no_power': self.search_count([('current_status', '=', 'NO_POWER')]),
            'moving': self.search_count([('is_moving', '=', True)]),
        }