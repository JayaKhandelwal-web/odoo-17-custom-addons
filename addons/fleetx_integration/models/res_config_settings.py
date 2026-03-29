# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Add the missing module field that's referenced in the XML view
    module_fleetx_integration = fields.Boolean(
        string='FleetX Integration Module',
        help='Install FleetX Integration Module'
    )
    
    # FleetX Configuration
    fleetx_base_url = fields.Char(
        string='FleetX API Base URL',
        config_parameter='fleetx_integration.base_url',
        default='https://api.fleetx.io/api/v1'
    )
    
    fleetx_access_token = fields.Char(
        string='FleetX Access Token',
        config_parameter='fleetx_integration.access_token'
    )
    
    fleetx_sync_interval = fields.Integer(
        string='Auto Sync Interval (minutes)',
        config_parameter='fleetx_integration.sync_interval',
        default=5
    )
    
    fleetx_auto_sync = fields.Boolean(
        string='Enable Auto Sync',
        config_parameter='fleetx_integration.auto_sync',
        default=True
    )
    
    fleetx_log_level = fields.Selection([
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ], string='Log Level',
       config_parameter='fleetx_integration.log_level',
       default='info')
    
    # Dashboard Settings
    fleetx_dashboard_refresh = fields.Integer(
        string='Dashboard Auto Refresh (seconds)',
        config_parameter='fleetx_integration.dashboard_refresh',
        default=30
    )
    
    fleetx_map_default_zoom = fields.Integer(
        string='Default Map Zoom Level',
        config_parameter='fleetx_integration.map_zoom',
        default=10
    )
    
    # Notification Settings
    fleetx_enable_notifications = fields.Boolean(
        string='Enable Notifications',
        config_parameter='fleetx_integration.enable_notifications',
        default=True
    )
    
    fleetx_notification_types = fields.Selection([
        ('all', 'All Events'),
        ('critical', 'Critical Only'),
        ('none', 'None'),
    ], string='Notification Types',
       config_parameter='fleetx_integration.notification_types',
       default='critical')

    def action_test_fleetx_connection(self):
        """Test FleetX API connection"""
        config = self.env['fleetx.config'].search([('active', '=', True)], limit=1)
        if not config:
            # Create a temporary config for testing
            config = self.env['fleetx.config'].create({
                'name': 'Test Configuration',
                'base_url': self.fleetx_base_url,
                'access_token': self.fleetx_access_token,
                'active': False,  # Don't activate it
            })
        else:
            # Update existing config with current settings
            config.write({
                'base_url': self.fleetx_base_url,
                'access_token': self.fleetx_access_token,
            })
        return config.test_connection()

    def action_sync_fleetx_data(self):
        """Manual sync FleetX data"""
        config = self.env['fleetx.config'].search([('active', '=', True)], limit=1)
        if config:
            return config.sync_vehicles()
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Configuration'),
                    'message': _('Please create and activate a FleetX configuration first.'),
                    'type': 'warning',
                }
            }

    def action_open_fleetx_dashboard(self):
        """Open FleetX dashboard"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('FleetX Dashboard'),
            'res_model': 'fleetx.analytics',
            'view_mode': 'kanban,tree,form',
            'target': 'current',
        }