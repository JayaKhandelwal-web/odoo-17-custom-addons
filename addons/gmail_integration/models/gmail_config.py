# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json
import requests
import logging

_logger = logging.getLogger(__name__)


class GmailConfiguration(models.Model):
    """
    Dedicated Gmail Configuration Model
    
    This replaces res.config.settings for Gmail to avoid conflicts
    with other modules (like muk_web_theme) that also extend system settings.
    
    Integrates all functionality from res_config_settings.py
    """
    _name = 'gmail.configuration'
    _description = 'Gmail OAuth Configuration'
    _rec_name = 'name'
    _order = 'id desc'

    # Basic Configuration
    name = fields.Char(
        string='Configuration Name',
        default='Gmail OAuth Configuration',
        required=True
    )
    
    # OAuth Settings (from res_config_settings.py)
    oauth_enabled = fields.Boolean(
        string='Enable Gmail Integration',
        default=False,
        help='Enable Gmail OAuth integration for all users'
    )
    
    client_id = fields.Char(
        string='Gmail Client ID',
        help='OAuth 2.0 Client ID from Google Cloud Console (shared for all users)'
    )
    
    client_secret = fields.Char(
        string='Gmail Client Secret',
        help='OAuth 2.0 Client Secret from Google Cloud Console (shared for all users)'
    )
    
    redirect_uri = fields.Char(
        string='OAuth Redirect URI',
        compute='_compute_redirect_uri',
        help='Use this URI in your Google Cloud Console OAuth configuration'
    )
    
    required_scopes = fields.Text(
        string='Required Gmail Scopes',
        compute='_compute_required_scopes',
        help='Gmail API scopes that will be requested'
    )
    
    # Default Settings for New Accounts (from res_config_settings.py)
    default_sync_frequency = fields.Selection([
        ('realtime', 'Real-time (Push)'),
        ('5min', 'Every 5 minutes'),
        ('15min', 'Every 15 minutes'),
        ('30min', 'Every 30 minutes'),
        ('1hour', 'Every hour'),
        ('manual', 'Manual only'),
    ], string='Default Sync Frequency', 
       default='realtime',
       help='Default sync frequency for new Gmail accounts')
    
    default_sync_folders = fields.Selection([
        ('inbox_sent', 'Inbox and Sent only'),
        ('all_important', 'All important folders'),
        ('all_folders', 'All folders'),
        ('custom', 'Custom selection'),
    ], string='Default Folders to Sync',
       default='inbox_sent',
       help='Default folders to sync for new accounts')
    
    # Configuration Status (from res_config_settings.py) - FIXED: Added store=True
    config_status = fields.Selection([
        ('not_configured', 'Not Configured'),
        ('configured', 'Configured'),
        ('error', 'Configuration Error'),
    ], string='Configuration Status',
       compute='_compute_config_status',
       store=True)  # FIXED: Added store=True to make it searchable
    
    config_message = fields.Text(
        string='Configuration Message',
        compute='_compute_config_status',
        store=True  # Also store this for consistency
    )
    
    # Statistics (from res_config_settings.py)
    total_accounts = fields.Integer(
        string='Connected Gmail Accounts',
        compute='_compute_statistics'
    )
    
    active_users = fields.Integer(
        string='Active Users',
        compute='_compute_statistics'
    )
    
    total_messages = fields.Integer(
        string='Total Synced Messages',
        compute='_compute_statistics'
    )
    
    last_sync_date = fields.Datetime(
        string='Last Sync Activity',
        compute='_compute_statistics'
    )
    
    # System Info
    is_active = fields.Boolean(
        string='Active Configuration',
        default=True,
        help='Only one configuration can be active at a time'
    )
    
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    last_test_date = fields.Datetime(
        string='Last Test Date',
        readonly=True
    )
    
    last_test_result = fields.Char(
        string='Last Test Result',
        readonly=True
    )

    # ============================================
    # COMPUTED FIELDS (from res_config_settings.py)
    # ============================================

    @api.depends()
    def _compute_redirect_uri(self):
        """Compute OAuth redirect URI"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.redirect_uri = f'{base_url}/gmail/auth/callback'
    
    @api.depends()
    def _compute_required_scopes(self):
        """Compute required Gmail scopes"""
        scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send', 
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/gmail.compose',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
        ]
        for record in self:
            record.required_scopes = '\n'.join([f'• {scope}' for scope in scopes])
    
    @api.depends('oauth_enabled', 'client_id', 'client_secret')
    def _compute_config_status(self):
        """Compute configuration status and validation message"""
        for record in self:
            if not record.oauth_enabled:
                record.config_status = 'not_configured'
                record.config_message = _('Gmail integration is disabled. Enable it to configure OAuth.')
                continue
            
            if not record.client_id or not record.client_secret:
                record.config_status = 'not_configured'
                record.config_message = _(
                    'Missing OAuth credentials. Please configure Client ID and Client Secret.\n\n'
                    'Steps:\n'
                    '1. Go to Google Cloud Console\n'
                    '2. Create or select a project\n'
                    '3. Enable Gmail API\n'
                    '4. Create OAuth 2.0 credentials\n'
                    '5. Add the redirect URI shown above\n'
                    '6. Copy Client ID and Secret here'
                )
                continue
            
            # Validate OAuth configuration
            try:
                validation_result = record._validate_oauth_config()
                if validation_result['valid']:
                    record.config_status = 'configured'
                    record.config_message = _(
                        'Gmail OAuth is properly configured ✅\n\n'
                        'Users can now connect their Gmail accounts using the shared OAuth app.\n'
                        'Total connected accounts: %d'
                    ) % record.total_accounts
                else:
                    record.config_status = 'error'
                    record.config_message = _(
                        'Configuration Error ❌\n\n'
                        'Issue: %s\n\n'
                        'Please check your OAuth credentials and Google Cloud Console configuration.'
                    ) % validation_result['error']
                    
            except Exception as e:
                record.config_status = 'error'
                record.config_message = _(
                    'Validation Error ❌\n\n'
                    'Could not validate OAuth configuration: %s'
                ) % str(e)
    
    @api.depends()
    def _compute_statistics(self):
        """Compute Gmail integration statistics"""
        for record in self:
            try:
                # Count connected accounts
                accounts = self.env['gmail.account'].search([
                    ('status', '=', 'connected')
                ])
                record.total_accounts = len(accounts)
                
                # Count unique users with connected accounts
                user_ids = accounts.mapped('user_id.id')
                record.active_users = len(set(user_ids)) if user_ids else 0
                
                # Count total messages
                try:
                    messages = self.env['gmail.message'].search([
                        ('account_id', 'in', accounts.ids)
                    ])
                    record.total_messages = len(messages)
                except:
                    record.total_messages = 0
                
                # Get last sync date
                if accounts:
                    last_sync_dates = accounts.mapped('last_sync_date')
                    valid_dates = [d for d in last_sync_dates if d]
                    record.last_sync_date = max(valid_dates) if valid_dates else False
                else:
                    record.last_sync_date = False
                
            except Exception as e:
                _logger.warning(f'Error computing Gmail statistics: {e}')
                record.total_accounts = 0
                record.active_users = 0
                record.total_messages = 0
                record.last_sync_date = False

    # ============================================
    # VALIDATION METHODS (from res_config_settings.py)
    # ============================================

    def _validate_oauth_config(self):
        """Validate OAuth configuration with Google"""
        self.ensure_one()
        
        if not self.client_id or not self.client_secret:
            return {'valid': False, 'error': 'Missing Client ID or Client Secret'}
        
        try:
            # Basic format validation
            if not self.client_id.endswith('.apps.googleusercontent.com'):
                return {
                    'valid': False, 
                    'error': 'Client ID format is invalid. Should end with .apps.googleusercontent.com'
                }
            
            if len(self.client_secret) < 20:
                return {
                    'valid': False,
                    'error': 'Client Secret seems too short. Please check your Google Cloud Console.'
                }
            
            return {'valid': True, 'error': None}
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}

    # ============================================
    # ACTION METHODS (from res_config_settings.py)
    # ============================================

    def action_test_oauth_config(self):
        """Test OAuth configuration"""
        self.ensure_one()
        
        try:
            result = self._validate_oauth_config()
            
            # Update test tracking
            self.write({
                'last_test_date': fields.Datetime.now(),
                'last_test_result': 'Success' if result['valid'] else f"Error: {result['error']}"
            })
            
            if result['valid']:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Configuration Valid'),
                        'message': _('Gmail OAuth configuration is valid and ready to use!'),
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Configuration Error'),
                        'message': _('Configuration issue: %s') % result['error'],
                        'type': 'danger',
                    }
                }
                
        except Exception as e:
            self.write({
                'last_test_date': fields.Datetime.now(),
                'last_test_result': f'Exception: {str(e)}'
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test Failed'),
                    'message': _('Failed to test configuration: %s') % str(e),
                    'type': 'danger',
                }
            }

    def action_open_google_console(self):
        """Open Google Cloud Console for OAuth setup"""
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://console.cloud.google.com/apis/credentials',
            'target': 'new',
        }

    def action_setup_guide(self):
        """Open Gmail OAuth setup guide"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/gmail/auth/setup_guide',
            'target': 'new',
        }

    def action_reset_oauth_config(self):
        """Reset OAuth configuration"""
        self.ensure_one()
        
        # Clear OAuth settings
        self.write({
            'oauth_enabled': False,
            'client_id': False,
            'client_secret': False,
        })
        
        # Disconnect all Gmail accounts
        connected_accounts = self.env['gmail.account'].search([
            ('status', '=', 'connected')
        ])
        
        for account in connected_accounts:
            try:
                account.action_disconnect_gmail()
            except Exception as e:
                _logger.warning(f'Failed to disconnect account {account.email_address}: {e}')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Configuration Reset'),
                'message': _('Gmail OAuth configuration has been reset. All accounts have been disconnected.'),
                'type': 'warning',
            }
        }

    def action_save_and_apply(self):
        """Save configuration and apply to system"""
        self.ensure_one()
        
        # Deactivate other configurations
        other_configs = self.search([('id', '!=', self.id)])
        other_configs.write({'is_active': False})
        
        # Activate this configuration
        self.is_active = True
        
        # Apply to system parameters
        self._apply_to_system()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Configuration Saved'),
                'message': _('Gmail configuration has been saved and applied to the system!'),
                'type': 'success',
            }
        }

    def _apply_to_system(self):
        """Apply configuration to system parameters"""
        self.ensure_one()
        
        # Set system parameters (same as res_config_settings)
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('gmail_integration.oauth_enabled', self.oauth_enabled)
        params.set_param('gmail_integration.client_id', self.client_id or '')
        params.set_param('gmail_integration.client_secret', self.client_secret or '')
        params.set_param('gmail_integration.default_sync_frequency', self.default_sync_frequency)
        params.set_param('gmail_integration.default_sync_folders', self.default_sync_folders)

    # ============================================
    # API METHODS (from res_config_settings.py)
    # ============================================

    @api.model
    def get_active_config(self):
        """Get the active Gmail configuration"""
        config = self.search([('is_active', '=', True)], limit=1)
        if not config:
            # Create default configuration if none exists
            config = self.create({
                'name': 'Default Gmail Configuration',
                'is_active': True,
            })
        return config

    @api.model
    def get_gmail_oauth_config(self):
        """Get Gmail OAuth configuration for controllers (replaces res.config.settings method)"""
        # Try new configuration first
        config = self.get_active_config()
        if config.oauth_enabled and config.client_id and config.client_secret:
            return {
                'enabled': config.oauth_enabled,
                'client_id': config.client_id,
                'client_secret': config.client_secret,
            }
        
        # Fallback to system parameters (for backward compatibility)
        return {
            'enabled': self.env['ir.config_parameter'].sudo().get_param('gmail_integration.oauth_enabled', False),
            'client_id': self.env['ir.config_parameter'].sudo().get_param('gmail_integration.client_id', ''),
            'client_secret': self.env['ir.config_parameter'].sudo().get_param('gmail_integration.client_secret', ''),
        }

    @api.model
    def is_gmail_oauth_configured(self):
        """Check if Gmail OAuth is properly configured (replaces res.config.settings method)"""
        config = self.get_gmail_oauth_config()
        return (
            config['enabled'] and 
            config['client_id'] and 
            config['client_secret']
        )

    # ============================================
    # MODEL LIFECYCLE METHODS
    # ============================================

    @api.model
    def create(self, vals):
        """Override create to ensure only one active configuration"""
        if vals.get('is_active', False):
            # Deactivate other configurations
            self.search([]).write({'is_active': False})
        
        config = super().create(vals)
        
        # Apply to system if active
        if config.is_active:
            config._apply_to_system()
        
        return config

    def write(self, vals):
        """Override write to handle active configuration changes"""
        if vals.get('is_active', False):
            # Deactivate other configurations
            other_configs = self.search([('id', 'not in', self.ids)])
            other_configs.write({'is_active': False})
        
        result = super().write(vals)
        
        # Apply to system if any active configuration was modified
        for config in self.filtered('is_active'):
            config._apply_to_system()
        
        return result

    # ============================================
    # BACKWARD COMPATIBILITY BRIDGE
    # ============================================

    @api.model
    def migrate_from_res_config_settings(self):
        """Migrate existing configuration from res.config.settings to dedicated model"""
        try:
            params = self.env['ir.config_parameter'].sudo()
            
            # Check if there's existing configuration
            oauth_enabled = params.get_param('gmail_integration.oauth_enabled', False)
            client_id = params.get_param('gmail_integration.client_id', '')
            client_secret = params.get_param('gmail_integration.client_secret', '')
            
            if oauth_enabled and client_id and client_secret:
                # Create configuration from existing parameters
                existing_config = self.search([('is_active', '=', True)], limit=1)
                if not existing_config:
                    self.create({
                        'name': 'Migrated Gmail Configuration',
                        'oauth_enabled': oauth_enabled,
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'default_sync_frequency': params.get_param('gmail_integration.default_sync_frequency', 'realtime'),
                        'default_sync_folders': params.get_param('gmail_integration.default_sync_folders', 'inbox_sent'),
                        'is_active': True,
                    })
                    _logger.info('Gmail configuration migrated from res.config.settings')
        except Exception as e:
            _logger.warning(f'Failed to migrate Gmail configuration: {e}')
