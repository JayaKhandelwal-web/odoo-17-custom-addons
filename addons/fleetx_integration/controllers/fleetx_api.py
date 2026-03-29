# -*- coding: utf-8 -*-
import json
import logging
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class FleetXAPIController(http.Controller):

    @http.route('/fleetx/webhook', type='json', auth='none', methods=['POST'], csrf=False)
    def fleetx_webhook(self, **kwargs):
        """FleetX webhook endpoint for real-time updates"""
        try:
            data = request.jsonrequest
            _logger.info(f'Received FleetX webhook data: {data}')
            
            # Process webhook data
            if data and 'vehicleId' in data:
                vehicle_id = str(data['vehicleId'])
                config = request.env['fleetx.config'].sudo().search([('active', '=', True)], limit=1)
                
                if config:
                    vehicle = request.env['fleetx.vehicle'].sudo().search([
                        ('vehicle_id', '=', vehicle_id),
                        ('config_id', '=', config.id)
                    ], limit=1)
                    
                    if vehicle:
                        # Update vehicle with webhook data
                        update_values = {}
                        
                        if 'latitude' in data:
                            update_values['latitude'] = data['latitude']
                        if 'longitude' in data:
                            update_values['longitude'] = data['longitude']
                        if 'speed' in data:
                            update_values['speed'] = data['speed']
                        if 'status' in data:
                            update_values['status'] = data['status']
                        if 'currentStatus' in data:
                            update_values['current_status'] = data['currentStatus']
                        
                        if update_values:
                            vehicle.write(update_values)
                            _logger.info(f'Updated vehicle {vehicle.vehicle_number} via webhook')
            
            return {'status': 'success', 'message': 'Webhook processed successfully'}
            
        except Exception as e:
            _logger.error(f'Error processing FleetX webhook: {str(e)}')
            return {'status': 'error', 'message': str(e)}

    @http.route('/fleetx/api/vehicles', type='json', auth='user', methods=['GET'])
    def get_vehicles(self, **kwargs):
        """API endpoint to get vehicles data"""
        try:
            domain = []
            
            # Filter by status if provided
            if kwargs.get('status'):
                domain.append(('current_status', '=', kwargs['status']))
            
            # Filter by config if provided
            if kwargs.get('config_id'):
                domain.append(('config_id', '=', int(kwargs['config_id'])))
            
            vehicles = request.env['fleetx.vehicle'].search(domain)
            
            vehicle_data = []
            for vehicle in vehicles:
                vehicle_data.append({
                    'id': vehicle.id,
                    'vehicle_number': vehicle.vehicle_number,
                    'vehicle_name': vehicle.vehicle_name,
                    'status': vehicle.current_status,
                    'speed': vehicle.speed,
                    'latitude': vehicle.latitude,
                    'longitude': vehicle.longitude,
                    'address': vehicle.address,
                    'fuel_percentage': vehicle.fuel_percentage,
                    'last_updated': vehicle.last_updated_at.isoformat() if vehicle.last_updated_at else None,
                })
            
            return {
                'status': 'success',
                'data': vehicle_data,
                'count': len(vehicle_data)
            }
            
        except Exception as e:
            _logger.error(f'Error getting vehicles data: {str(e)}')
            return {'status': 'error', 'message': str(e)}

    @http.route('/fleetx/api/analytics', type='json', auth='user', methods=['GET'])
    def get_analytics(self, **kwargs):
        """API endpoint to get analytics data"""
        try:
            config_id = kwargs.get('config_id')
            analytics_data = request.env['fleetx.analytics'].get_latest_analytics(config_id)
            
            return {
                'status': 'success',
                'data': analytics_data
            }
            
        except Exception as e:
            _logger.error(f'Error getting analytics data: {str(e)}')
            return {'status': 'error', 'message': str(e)}

    @http.route('/fleetx/api/sync', type='json', auth='user', methods=['POST'])
    def sync_data(self, **kwargs):
        """API endpoint to trigger manual sync"""
        try:
            config_id = kwargs.get('config_id')
            
            if config_id:
                config = request.env['fleetx.config'].browse(int(config_id))
            else:
                config = request.env['fleetx.config'].search([('active', '=', True)], limit=1)
            
            if not config:
                return {'status': 'error', 'message': 'No active FleetX configuration found'}
            
            result = config.sync_vehicles()
            
            return {
                'status': 'success',
                'message': 'Data synchronized successfully',
                'data': result
            }
            
        except Exception as e:
            _logger.error(f'Error syncing data: {str(e)}')
            return {'status': 'error', 'message': str(e)}

    @http.route('/fleetx/api/vehicle/<int:vehicle_id>', type='json', auth='user', methods=['GET'])
    def get_vehicle_details(self, vehicle_id, **kwargs):
        """API endpoint to get specific vehicle details"""
        try:
            vehicle = request.env['fleetx.vehicle'].browse(vehicle_id)
            
            if not vehicle.exists():
                return {'status': 'error', 'message': 'Vehicle not found'}
            
            vehicle_data = {
                'id': vehicle.id,
                'vehicle_id': vehicle.vehicle_id,
                'vehicle_number': vehicle.vehicle_number,
                'vehicle_name': vehicle.vehicle_name,
                'make': vehicle.vehicle_make,
                'model': vehicle.vehicle_model,
                'year': vehicle.vehicle_year,
                'type': vehicle.vehicle_type_value,
                'fuel_type': vehicle.fuel_type,
                'driver_name': vehicle.driver_name,
                'status': vehicle.current_status,
                'speed': vehicle.speed,
                'latitude': vehicle.latitude,
                'longitude': vehicle.longitude,
                'address': vehicle.address,
                'current_fuel': vehicle.current_fuel,
                'fuel_percentage': vehicle.fuel_percentage,
                'fuel_tank_capacity': vehicle.fuel_tank_capacity,
                'total_odometer': vehicle.total_odometer,
                'trip_odometer': vehicle.trip_odometer,
                'mileage': vehicle.mileage,
                'last_updated': vehicle.last_updated_at.isoformat() if vehicle.last_updated_at else None,
                'last_status_time': vehicle.last_status_time.isoformat() if vehicle.last_status_time else None,
                'device_id': vehicle.device_id,
                'is_moving': vehicle.is_moving,
                'location_link': vehicle.location_link,
                'other_attributes': vehicle.other_attributes,
            }
            
            return {
                'status': 'success',
                'data': vehicle_data
            }
            
        except Exception as e:
            _logger.error(f'Error getting vehicle details: {str(e)}')
            return {'status': 'error', 'message': str(e)}

    @http.route('/fleetx/api/dashboard', type='json', auth='user', methods=['GET'])
    def get_dashboard_data(self, **kwargs):
        """API endpoint to get dashboard data"""
        try:
            config_id = kwargs.get('config_id')
            
            # Get vehicle statistics
            vehicle_stats = request.env['fleetx.vehicle'].get_vehicle_statistics()
            
            # Get latest analytics
            analytics_data = request.env['fleetx.analytics'].get_latest_analytics(config_id)
            
            # Get chart data
            days = kwargs.get('days', 7)
            chart_data = request.env['fleetx.analytics'].get_analytics_chart_data(days, config_id)
            
            # Get recent vehicles
            recent_vehicles = request.env['fleetx.vehicle'].search([
                ('last_updated_at', '!=', False)
            ], limit=10, order='last_updated_at desc')
            
            recent_vehicles_data = []
            for vehicle in recent_vehicles:
                recent_vehicles_data.append({
                    'id': vehicle.id,
                    'vehicle_number': vehicle.vehicle_number,
                    'status': vehicle.current_status,
                    'speed': vehicle.speed,
                    'last_updated': vehicle.last_updated_at.isoformat() if vehicle.last_updated_at else None,
                })
            
            dashboard_data = {
                'vehicle_statistics': vehicle_stats,
                'analytics': analytics_data,
                'chart_data': chart_data,
                'recent_vehicles': recent_vehicles_data,
                'last_sync': analytics_data.get('create_date'),
            }
            
            return {
                'status': 'success',
                'data': dashboard_data
            }
            
        except Exception as e:
            _logger.error(f'Error getting dashboard data: {str(e)}')
            return {'status': 'error', 'message': str(e)}