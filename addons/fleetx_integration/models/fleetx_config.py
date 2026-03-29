# -*- coding: utf-8 -*-
# Fix for fleetx_config.py - Updated sync method with better error handling

import requests
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class FleetXConfig(models.Model):
    _name = 'fleetx.config'
    _description = 'FleetX API Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', required=True, default='FleetX API')
    base_url = fields.Char(
        string='API Base URL',
        required=True,
        default='https://api.fleetx.io/api/v1',
        help='FleetX API base URL'
    )
    access_token = fields.Char(
        string='Access Token',
        required=True,
        help='FleetX API access token'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    active = fields.Boolean(string='Active', default=True)
    sync_interval = fields.Integer(
        string='Sync Interval (minutes)',
        default=5,
        help='Interval for automatic data synchronization in minutes'
    )
    last_sync = fields.Datetime(string='Last Sync', readonly=True)
    sync_status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('pending', 'Pending')
    ], string='Sync Status', default='pending', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)

    # Statistics
    total_vehicles = fields.Integer(string='Total Vehicles', readonly=True)
    running_vehicles = fields.Integer(string='Running Vehicles', readonly=True)
    idle_vehicles = fields.Integer(string='Idle Vehicles', readonly=True)
    parked_vehicles = fields.Integer(string='Parked Vehicles', readonly=True)

    @api.constrains('access_token', 'active')
    def _check_access_token(self):
        for record in self:
            if record.active and not record.access_token:
                raise ValidationError(_('Access token is required for active FleetX API configurations.'))

    @api.constrains('sync_interval')
    def _check_sync_interval(self):
        for record in self:
            if record.sync_interval < 1:
                raise ValidationError(_('Sync interval must be at least 1 minute.'))

    def test_connection(self):
        """Test FleetX API connection"""
        if not self.access_token:
            raise UserError(_('Access token is required to test the connection.'))

        try:
            headers = {
                'Authorization': f'bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            response = requests.get(
                f'{self.base_url}/analytics/live',
                headers=headers,
                timeout=30
            )

            _logger.info(f'API Response Status: {response.status_code}')
            _logger.info(f'API Response Content: {response.text[:500]}...')

            if response.status_code == 200:
                data = response.json()
                self.write({
                    'sync_status': 'success',
                    'error_message': False,
                    'last_sync': fields.Datetime.now(),
                    'total_vehicles': data.get('totalVehicles', 0),
                    'running_vehicles': data.get('runningVehicles', 0),
                    'idle_vehicles': data.get('idleVehicles', 0),
                    'parked_vehicles': data.get('parkedVehicles', 0),
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Successful'),
                        'message': _('FleetX API connection is working correctly. Found %s vehicles.') % data.get(
                            'totalVehicles', 0),
                        'type': 'success',
                    }
                }
            else:
                error_msg = f'API returned status {response.status_code}: {response.text}'
                self.write({
                    'sync_status': 'error',
                    'error_message': error_msg
                })
                raise UserError(_('Connection failed: %s') % error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f'Connection error: {str(e)}'
            self.write({
                'sync_status': 'error',
                'error_message': error_msg
            })
            raise UserError(_('Connection failed: %s') % error_msg)

    def sync_vehicles(self):
        """Sync vehicles from FleetX API - IMPROVED VERSION"""
        try:
            if not self.access_token:
                raise UserError(_('Access token is required for synchronization.'))

            headers = {
                'Authorization': f'bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            _logger.info(f'Starting sync for config: {self.name}')

            response = requests.get(
                f'{self.base_url}/analytics/live',
                headers=headers,
                timeout=30
            )

            _logger.info(f'Sync API Response Status: {response.status_code}')

            if response.status_code == 200:
                data = response.json()

                # Log the response structure for debugging
                _logger.info(f'API Response keys: {list(data.keys())}')
                _logger.info(f'Total vehicles in response: {data.get("totalVehicles", 0)}')

                vehicles_data = data.get('vehicles', [])
                _logger.info(f'Vehicles array length: {len(vehicles_data)}')

                if not vehicles_data:
                    _logger.warning('No vehicles found in API response')
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Sync Completed'),
                            'message': _('No vehicles found in FleetX API response'),
                            'type': 'warning',
                        }
                    }

                # Update configuration statistics first
                self.write({
                    'sync_status': 'success',
                    'error_message': False,
                    'last_sync': fields.Datetime.now(),
                    'total_vehicles': data.get('totalVehicles', 0),
                    'running_vehicles': data.get('runningVehicles', 0),
                    'idle_vehicles': data.get('idleVehicles', 0),
                    'parked_vehicles': data.get('parkedVehicles', 0),
                })

                # Sync vehicles with detailed error tracking
                vehicle_model = self.env['fleetx.vehicle']
                created_count = 0
                updated_count = 0
                error_count = 0
                error_details = []

                for i, vehicle_data in enumerate(vehicles_data):
                    try:
                        vehicle_number = vehicle_data.get('vehicleNumber', f'Unknown_{i}')
                        vehicle_id = str(vehicle_data.get('vehicleId', ''))

                        _logger.info(
                            f'Processing vehicle {i + 1}/{len(vehicles_data)}: {vehicle_number} (ID: {vehicle_id})')

                        # Check if vehicle exists
                        existing_vehicle = vehicle_model.search([
                            ('vehicle_id', '=', vehicle_id),
                            ('config_id', '=', self.id)
                        ], limit=1)

                        # Process the vehicle
                        result = vehicle_model.create_or_update_vehicle(vehicle_data, self.id)

                        if result:
                            if existing_vehicle:
                                updated_count += 1
                                _logger.info(f'Successfully updated vehicle: {vehicle_number}')
                            else:
                                created_count += 1
                                _logger.info(f'Successfully created vehicle: {vehicle_number}')
                        else:
                            error_count += 1
                            error_msg = f'Failed to process vehicle: {vehicle_number}'
                            error_details.append(error_msg)
                            _logger.error(error_msg)

                    except Exception as e:
                        error_count += 1
                        vehicle_number = vehicle_data.get('vehicleNumber', f'Unknown_{i}')
                        error_msg = f'Exception processing vehicle {vehicle_number}: {str(e)}'
                        error_details.append(error_msg)
                        _logger.error(error_msg)
                        continue

                # Create analytics record
                try:
                    analytics_model = self.env['fleetx.analytics']
                    analytics_model.create_analytics_record(data, self.id)
                    _logger.info('Analytics record created successfully')
                except Exception as e:
                    _logger.error(f'Failed to create analytics record: {str(e)}')

                # Log final results
                _logger.info(
                    f'Sync completed - Created: {created_count}, Updated: {updated_count}, Errors: {error_count}')

                if error_details:
                    _logger.error('Error details:')
                    for error in error_details[:10]:  # Log first 10 errors
                        _logger.error(f'  - {error}')
                    if len(error_details) > 10:
                        _logger.error(f'  ... and {len(error_details) - 10} more errors')

                # Update sync status based on results
                if error_count == len(vehicles_data):
                    # All vehicles failed
                    self.write({
                        'sync_status': 'error',
                        'error_message': f'All {len(vehicles_data)} vehicles failed to sync. Check logs for details.'
                    })
                    message_type = 'error'
                elif error_count > 0:
                    # Some vehicles failed
                    self.write({
                        'sync_status': 'success',
                        'error_message': f'{error_count} vehicles failed to sync. Check logs for details.'
                    })
                    message_type = 'warning'
                else:
                    # All vehicles succeeded
                    self.write({
                        'sync_status': 'success',
                        'error_message': False
                    })
                    message_type = 'success'

                message = _(
                    'Sync completed!\n'
                    'Created: %d vehicles\n'
                    'Updated: %d vehicles\n'
                    'Errors: %d vehicles'
                ) % (created_count, updated_count, error_count)

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Sync Completed'),
                        'message': message,
                        'type': message_type,
                    }
                }
            else:
                error_msg = f'API returned status {response.status_code}: {response.text}'
                self.write({
                    'sync_status': 'error',
                    'error_message': error_msg
                })
                raise UserError(_('Sync failed: %s') % error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f'Sync error: {str(e)}'
            self.write({
                'sync_status': 'error',
                'error_message': error_msg
            })
            raise UserError(_('Sync failed: %s') % error_msg)

    @api.model
    def auto_sync_vehicles(self):
        """Automatic sync method called by cron job"""
        configs = self.search([('active', '=', True)])
        for config in configs:
            try:
                _logger.info(f'Auto sync starting for config: {config.name}')
                config.sync_vehicles()
            except Exception as e:
                _logger.error(f'Auto sync failed for config {config.name}: {str(e)}')

    @api.model
    def cron_health_check(self):
        """Health check for all active configurations (called by cron)"""
        configs = self.search([('active', '=', True)])
        for config in configs:
            try:
                config.test_connection()
                _logger.info(f'Health check passed for config {config.name}')
            except Exception as e:
                _logger.error(f'Health check failed for config {config.name}: {str(e)}')
                config.write({
                    'sync_status': 'error',
                    'error_message': f'Health check failed: {str(e)}'
                })

    def action_manual_sync(self):
        """Manual sync action"""
        return self.sync_vehicles()