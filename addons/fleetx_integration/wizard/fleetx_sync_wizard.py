# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FleetXSyncWizard(models.TransientModel):
    _name = 'fleetx.sync.wizard'
    _description = 'FleetX Data Synchronization Wizard'

    config_id = fields.Many2one(
        'fleetx.config',
        string='Configuration',
        required=True,
        domain=[('active', '=', True)]
    )
    sync_type = fields.Selection([
        ('full', 'Full Synchronization'),
        ('vehicles_only', 'Vehicles Only'),
        ('analytics_only', 'Analytics Only'),
    ], string='Sync Type', default='full', required=True)

    force_update = fields.Boolean(
        string='Force Update Existing Records',
        default=False,
        help='Update existing vehicle records even if they have not changed'
    )

    clear_existing = fields.Boolean(
        string='Clear Existing Data',
        default=False,
        help='Remove all existing vehicles before sync (use with caution)'
    )

    test_connection = fields.Boolean(
        string='Test Connection First',
        default=True,
        help='Test API connection before starting synchronization'
    )

    # Results
    sync_completed = fields.Boolean(string='Sync Completed', default=False)
    vehicles_created = fields.Integer(string='Vehicles Created', default=0)
    vehicles_updated = fields.Integer(string='Vehicles Updated', default=0)
    analytics_created = fields.Integer(string='Analytics Records Created', default=0)
    error_message = fields.Text(string='Error Message')
    sync_log = fields.Text(string='Sync Log')

    @api.model
    def default_get(self, fields_list):
        """Set default configuration"""
        res = super().default_get(fields_list)
        if 'config_id' in fields_list:
            config = self.env['fleetx.config'].search([('active', '=', True)], limit=1)
            if config:
                res['config_id'] = config.id
        return res

    def action_test_connection(self):
        """Test API connection"""
        self.ensure_one()
        try:
            result = self.config_id.test_connection()
            self.sync_log = "Connection test successful\n"
            return result
        except Exception as e:
            self.error_message = str(e)
            self.sync_log = f"Connection test failed: {str(e)}\n"
            raise UserError(_('Connection test failed: %s') % str(e))

    def action_start_sync(self):
        """Start synchronization process"""
        self.ensure_one()

        try:
            log_messages = []

            # Test connection if requested
            if self.test_connection:
                log_messages.append("Testing API connection...")
                self.config_id.test_connection()
                log_messages.append("✓ Connection test successful")

            # Clear existing data if requested
            if self.clear_existing:
                log_messages.append("Clearing existing data...")
                if self.sync_type in ['full', 'vehicles_only']:
                    vehicle_count = self.env['fleetx.vehicle'].search_count([
                        ('config_id', '=', self.config_id.id)
                    ])
                    self.env['fleetx.vehicle'].search([
                        ('config_id', '=', self.config_id.id)
                    ]).unlink()
                    log_messages.append(f"✓ Removed {vehicle_count} existing vehicles")

                if self.sync_type in ['full', 'analytics_only']:
                    analytics_count = self.env['fleetx.analytics'].search_count([
                        ('config_id', '=', self.config_id.id)
                    ])
                    self.env['fleetx.analytics'].search([
                        ('config_id', '=', self.config_id.id)
                    ]).unlink()
                    log_messages.append(f"✓ Removed {analytics_count} existing analytics records")

            # Start synchronization
            if self.sync_type in ['full', 'vehicles_only', 'analytics_only']:
                log_messages.append("Starting data synchronization...")

                # Get initial counts
                initial_vehicle_count = self.env['fleetx.vehicle'].search_count([
                    ('config_id', '=', self.config_id.id)
                ])
                initial_analytics_count = self.env['fleetx.analytics'].search_count([
                    ('config_id', '=', self.config_id.id)
                ])

                # Perform sync
                self.config_id.sync_vehicles()

                # Get final counts
                final_vehicle_count = self.env['fleetx.vehicle'].search_count([
                    ('config_id', '=', self.config_id.id)
                ])
                final_analytics_count = self.env['fleetx.analytics'].search_count([
                    ('config_id', '=', self.config_id.id)
                ])

                # Calculate results
                self.vehicles_created = max(0, final_vehicle_count - initial_vehicle_count)
                self.vehicles_updated = max(0, initial_vehicle_count - (0 if self.clear_existing else 0))
                self.analytics_created = max(0, final_analytics_count - initial_analytics_count)

                log_messages.append(f"✓ Vehicles created: {self.vehicles_created}")
                log_messages.append(f"✓ Vehicles updated: {self.vehicles_updated}")
                log_messages.append(f"✓ Analytics records created: {self.analytics_created}")
                log_messages.append("✓ Synchronization completed successfully")

            self.sync_completed = True
            self.sync_log = "\n".join(log_messages)
            self.error_message = False

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'fleetx.sync.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'sync_completed': True}
            }

        except Exception as e:
            error_msg = str(e)
            _logger.error(f'Sync wizard error: {error_msg}')
            self.error_message = error_msg
            self.sync_log = "\n".join(log_messages + [f"✗ Error: {error_msg}"])

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'fleetx.sync.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'sync_error': True}
            }

    def action_view_vehicles(self):
        """View synchronized vehicles"""
        self.ensure_one()
        return {
            'name': _('Synchronized Vehicles'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleetx.vehicle',
            'view_mode': 'tree,form',
            'domain': [('config_id', '=', self.config_id.id)],
            'context': {'default_config_id': self.config_id.id},
        }

    def action_view_analytics(self):
        """View analytics data"""
        self.ensure_one()
        return {
            'name': _('Analytics Data'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleetx.analytics',
            'view_mode': 'tree,form',
            'domain': [('config_id', '=', self.config_id.id)],
            'context': {'default_config_id': self.config_id.id},
        }

    def action_close(self):
        """Close wizard"""
        return {'type': 'ir.actions.act_window_close'}