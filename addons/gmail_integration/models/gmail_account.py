# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.cloud import pubsub_v1
    from google.api_core.exceptions import AlreadyExists, NotFound
    import requests
except ImportError:
    logging.getLogger(__name__).warning(
        'Google API libraries not found. Install: pip install google-auth google-auth-oauthlib google-api-python-client google-cloud-pubsub requests'
    )

_logger = logging.getLogger(__name__)


class GmailAccount(models.Model):
    _name = 'gmail.account'
    _description = 'Gmail Account Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'user_id, create_date desc'

    # === USER OWNERSHIP AND SHARING ===
    user_id = fields.Many2one(
        'res.users',
        string='Owner',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        help='User who owns this Gmail account'
    )
    
    shared_user_ids = fields.Many2many(
        'res.users',
        'gmail_account_shared_users_rel',
        'account_id',
        'user_id',
        string='Shared With Users',
        help='Users who can access this Gmail account'
    )
    
    access_level = fields.Selection([
        ('private', 'Private (Owner Only)'),
        ('shared', 'Shared with Selected Users'),
        ('company', 'Company Wide'),
    ], string='Access Level', 
       default='private',
       tracking=True,
       help='Who can access this Gmail account')
    
    # === BASIC ACCOUNT INFORMATION ===
    name = fields.Char(
        string='Account Name',
        required=True,
        tracking=True,
        help='Display name for this Gmail account'
    )
    
    email_address = fields.Char(
        string='Email Address',
        required=True,
        tracking=True,
        help='Gmail email address'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Computed display name'
    )
    
    # === OAUTH TOKENS (NO MORE CLIENT_ID/SECRET) ===
    access_token = fields.Text(
        string='Access Token',
        help='OAuth access token for API calls'
    )
    
    refresh_token = fields.Text(
        string='Refresh Token',
        help='OAuth refresh token for token renewal'
    )
    
    token_expires_at = fields.Datetime(
        string='Token Expires At',
        help='When the access token expires'
    )
    
    # === OAUTH SYSTEM INFORMATION ===
    oauth_uid = fields.Char(
        string='OAuth User ID',
        help='Google OAuth user identifier',
        readonly=True
    )
    
    authorized_scopes = fields.Text(
        string='Authorized Scopes',
        help='OAuth scopes granted by user',
        readonly=True
    )
    
    last_oauth_date = fields.Datetime(
        string='Last OAuth Date',
        help='When user last completed OAuth flow',
        readonly=True
    )
    
    # === PUBSUB CONFIGURATION ===
    google_project_id = fields.Char(
        string='Google Cloud Project ID',
        help='Google Cloud Project ID for Pub/Sub'
    )
    
    service_account_key = fields.Text(
        string='Service Account Key (JSON)',
        help='JSON service account key for Pub/Sub access'
    )
    
    pubsub_topic_name = fields.Char(
        string='Pub/Sub Topic Name',
        compute='_compute_pubsub_topic_name',
        help='Generated Pub/Sub topic name'
    )
    
    pubsub_subscription_name = fields.Char(
        string='Pub/Sub Subscription Name',
        compute='_compute_pubsub_subscription_name',
        help='Generated Pub/Sub subscription name'
    )
    
    # === GMAIL API SETTINGS ===
    history_id = fields.Char(
        string='History ID',
        help='Gmail history ID for incremental sync'
    )
    
    watch_expiration = fields.Datetime(
        string='Watch Expiration',
        help='When Gmail push notifications expire'
    )
    
    # === PUBSUB STATUS ===
    pubsub_topic_created = fields.Boolean(
        string='Pub/Sub Topic Created',
        default=False,
        help='Whether Pub/Sub topic has been created'
    )
    
    pubsub_subscription_created = fields.Boolean(
        string='Pub/Sub Subscription Created',
        default=False,
        help='Whether push subscription has been created'
    )
    
    gmail_watch_active = fields.Boolean(
        string='Gmail Watch Active',
        default=False,
        help='Whether Gmail watch is active'
    )
    
    pubsub_topic = fields.Char(
        string='Pub/Sub Topic (Full Path)',
        compute='_compute_pubsub_topic_full',
        help='Full Pub/Sub topic path'
    )
    
    # === SYNC CONFIGURATION ===
    sync_enabled = fields.Boolean(
        string='Enable Sync',
        default=True,
        help='Enable email synchronization'
    )
    
    sync_frequency = fields.Selection([
        ('realtime', 'Real-time (Push)'),
        ('5min', 'Every 5 minutes'),
        ('15min', 'Every 15 minutes'),
        ('30min', 'Every 30 minutes'),
        ('1hour', 'Every hour'),
        ('manual', 'Manual only'),
    ], string='Sync Frequency', default='realtime')
    
    # === FOLDER SYNC SETTINGS ===
    sync_inbox = fields.Boolean(string='Sync Inbox', default=True)
    sync_sent = fields.Boolean(string='Sync Sent', default=True)
    sync_drafts = fields.Boolean(string='Sync Drafts', default=False)
    sync_spam = fields.Boolean(string='Sync Spam', default=False)
    sync_trash = fields.Boolean(string='Sync Trash', default=False)
    
    # === STATUS AND HEALTH ===
    status = fields.Selection([
        ('draft', 'Not Connected'),
        ('connecting', 'Connecting'),
        ('connected', 'Connected'),
        ('error', 'Error'),
        ('expired', 'Token Expired'),
        ('suspended', 'Suspended'),
        ('oauth_required', 'OAuth Required'),
    ], string='Status', 
       default='draft', 
       tracking=True)
    
    last_sync_date = fields.Datetime(string='Last Sync Date')
    last_error_message = fields.Text(string='Last Error Message')
    
    # === STATISTICS ===
    total_messages = fields.Integer(
        string='Total Messages',
        compute='_compute_message_stats',
        help='Total number of synced messages'
    )
    
    unread_messages = fields.Integer(
        string='Unread Messages',
        compute='_compute_message_stats',
        help='Number of unread messages'
    )
    
    # === API QUOTA MANAGEMENT ===
    daily_quota_used = fields.Integer(string='Daily Quota Used', default=0)
    daily_quota_limit = fields.Integer(string='Daily Quota Limit', default=1000000000)
    quota_percentage = fields.Float(
        string='Quota Usage %',
        compute='_compute_quota_percentage'
    )
    
    # === RELATIONS ===
    message_ids = fields.One2many(
        'gmail.message',
        'account_id',
        string='Messages'
    )
    
    sync_log_ids = fields.One2many(
        'gmail.sync.log',
        'account_id',
        string='Sync Logs'
    )
    
    # === CONSTRAINTS ===
    _sql_constraints = [
        ('unique_user_email', 'unique(user_id, email_address)', 
         'Each user can only have one Gmail account per email address!'),
    ]
    
    # === COMPUTED FIELDS ===
    @api.depends('name', 'email_address', 'user_id')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.email_address:
                if record.user_id and record.user_id != self.env.user:
                    record.display_name = f"{record.name} ({record.email_address}) - {record.user_id.name}"
                else:
                    record.display_name = f"{record.name} ({record.email_address})"
            elif record.email_address:
                record.display_name = record.email_address
            else:
                record.display_name = record.name or 'New Gmail Account'
    
    @api.depends('email_address', 'user_id')
    def _compute_pubsub_topic_name(self):
        for record in self:
            if record.email_address and record.user_id:
                safe_email = record.email_address.replace('@', '-').replace('.', '-').lower()
                user_suffix = str(record.user_id.id)
                timestamp = str(int(datetime.now().timestamp()))[-6:]
                record.pubsub_topic_name = f'gmail-{safe_email}-u{user_suffix}-{timestamp}'
            else:
                record.pubsub_topic_name = ''
    
    @api.depends('pubsub_topic_name')
    def _compute_pubsub_subscription_name(self):
        for record in self:
            if record.pubsub_topic_name:
                record.pubsub_subscription_name = f'{record.pubsub_topic_name}-webhook'
            else:
                record.pubsub_subscription_name = ''
    
    @api.depends('google_project_id', 'pubsub_topic_name')
    def _compute_pubsub_topic_full(self):
        for record in self:
            if record.google_project_id and record.pubsub_topic_name:
                record.pubsub_topic = f'projects/{record.google_project_id}/topics/{record.pubsub_topic_name}'
            else:
                record.pubsub_topic = ''
    
    @api.depends('message_ids')
    def _compute_message_stats(self):
        for record in self:
            try:
                messages = record.message_ids
                record.total_messages = len(messages)
                record.unread_messages = len(messages.filtered(lambda m: not m.is_read))
            except Exception as e:
                _logger.warning(f"Error computing message stats for {record.email_address}: {e}")
                record.total_messages = 0
                record.unread_messages = 0
    
    @api.depends('daily_quota_used', 'daily_quota_limit')
    def _compute_quota_percentage(self):
        for record in self:
            if record.daily_quota_limit > 0:
                record.quota_percentage = (record.daily_quota_used / record.daily_quota_limit) * 100
            else:
                record.quota_percentage = 0
    
    # === VALIDATION ===
    @api.constrains('email_address')
    def _check_email_format(self):
        import re
        for record in self:
            if record.email_address:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, record.email_address):
                    raise ValidationError(_('Please enter a valid email address'))
    
    @api.constrains('shared_user_ids', 'access_level')
    def _check_shared_users(self):
        for record in self:
            if record.access_level == 'shared' and not record.shared_user_ids:
                raise ValidationError(_('Please select users to share this account with, or change access level.'))
    
    @api.constrains('service_account_key')
    def _check_service_account_key(self):
        """Validate service account key JSON format"""
        for record in self:
            if record.service_account_key:
                try:
                    key_data = json.loads(record.service_account_key)
                    required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                    for field in required_fields:
                        if field not in key_data:
                            raise ValidationError(_(f'Service account key missing required field: {field}'))
                except json.JSONDecodeError:
                    raise ValidationError(_('Service account key must be valid JSON'))
    
    # === SECURITY METHODS ===
    def _check_access_rights(self, operation='read'):
        """Enhanced access rights checking"""
        for record in self:
            user = self.env.user
            
            # Owner always has access
            if record.user_id == user:
                return True
            
            # Admin always has access
            if user.has_group('base.group_system'):
                return True
            
            # Check access level
            if record.access_level == 'private':
                if operation == 'read':
                    # Private accounts can be read by owner only
                    return False
                else:
                    # Write/delete only by owner
                    return False
            
            elif record.access_level == 'shared':
                # Check if user is in shared list
                if user in record.shared_user_ids:
                    return True
                return False
            
            elif record.access_level == 'company':
                # Company-wide access for same company users
                if user.company_id == record.user_id.company_id:
                    return True
                return False
            
            return False
    
    @api.model
    def search(self, domain, offset=0, limit=None, order=None, count=False):
        """Override search to apply user access controls - FIXED"""
        if self.env.user.has_group('base.group_system'):
            # Admin sees everything
            if count:
                return super().search_count(domain)
            return super().search(domain, offset=offset, limit=limit, order=order)
        
        # Add user access domain
        user_domain = [
            '|', '|', '|',
            ('user_id', '=', self.env.user.id),  # Owner
            '&', ('access_level', '=', 'shared'), ('shared_user_ids', 'in', [self.env.user.id]),  # Shared
            '&', ('access_level', '=', 'company'), ('user_id.company_id', '=', self.env.user.company_id.id),  # Company
            ('access_level', '=', 'company')  # Fallback for company access
        ]
        
        domain = domain + user_domain
        if count:
            return super().search_count(domain)
        return super().search(domain, offset=offset, limit=limit, order=order)
    
    # === DEBUG OAUTH METHODS (USING SHARED OAUTH APP) ===
    def action_connect_gmail(self):
        """Start OAuth flow by redirecting to controller - WITH COMPLETE DEBUG"""
        _logger.info(f'=== ACTION_CONNECT_GMAIL CALLED for {self.email_address} ===')
        _logger.info(f'Account ID: {self.id}')
        _logger.info(f'Current user: {self.env.user.name}')
        
        self.ensure_one()
        
        try:
            # Debug: Check system OAuth configuration
            _logger.info('Step 1: Checking system OAuth configuration...')
            
            # Check if the method exists
            if not hasattr(self, '_is_system_oauth_configured'):
                _logger.error('_is_system_oauth_configured method not found')
                raise UserError(_('System OAuth configuration method not found. Please contact administrator.'))
            
            # Check if method is callable
            method = getattr(self, '_is_system_oauth_configured')
            _logger.info(f'Method object: {method}')
            _logger.info(f'Method type: {type(method)}')
            
            if method is None:
                _logger.error('_is_system_oauth_configured method is None')
                raise UserError(_('System OAuth configuration method is None. Please contact administrator.'))
            
            if not callable(method):
                _logger.error(f'_is_system_oauth_configured is not callable: {type(method)}')
                raise UserError(_('System OAuth configuration method is not callable. Please contact administrator.'))
            
            # Call the method safely
            _logger.info('Step 2: Calling _is_system_oauth_configured...')
            try:
                is_configured = method()
                _logger.info(f'System OAuth configured result: {is_configured}')
            except Exception as e:
                _logger.error(f'Error calling _is_system_oauth_configured: {e}', exc_info=True)
                raise UserError(_('Error checking system OAuth configuration: %s') % str(e))
            
            if not is_configured:
                _logger.error('System OAuth not configured - stopping process')
                raise UserError(_(
                    'Gmail OAuth is not configured at system level.\n\n'
                    'Please ask your administrator to configure Gmail integration '
                    'in Gmail Settings.'
                ))
            
            # Update status
            _logger.info('Step 3: Setting account status to connecting...')
            try:
                self.status = 'connecting'
                _logger.info('Status updated successfully')
            except Exception as e:
                _logger.error(f'Error updating status: {e}')
                raise UserError(_('Error updating account status: %s') % str(e))
            
            # Build redirect URL
            redirect_url = f'/gmail/auth?account_id={self.id}'
            _logger.info(f'Step 4: Built redirect URL: {redirect_url}')
            
            # Prepare return action
            action = {
                'type': 'ir.actions.act_url',
                'url': redirect_url,
                'target': 'new',
            }
            _logger.info(f'Step 5: Returning action: {action}')
            _logger.info('=== ACTION_CONNECT_GMAIL COMPLETED SUCCESSFULLY ===')
            
            return action
            
        except UserError:
            # Re-raise UserError as-is
            raise
        except Exception as e:
            _logger.error(f'CRITICAL ERROR in action_connect_gmail: {e}', exc_info=True)
            raise UserError(_('Critical error starting Gmail connection: %s') % str(e))
    
    def _is_system_oauth_configured(self):
        """Check if system-level OAuth is configured - WITH COMPLETE DEBUG"""
        try:
            _logger.info('=== _IS_SYSTEM_OAUTH_CONFIGURED CALLED ===')
            
            # Check if gmail.configuration model exists
            _logger.info('Step 1: Checking gmail.configuration model existence...')
            if 'gmail.configuration' not in self.env:
                _logger.error('gmail.configuration model not found in environment')
                _logger.info(f'Available models: {list(self.env.registry.keys())[:10]}...')  # Show first 10 models
                return False
            
            _logger.info('gmail.configuration model found')
            
            # Get the model
            _logger.info('Step 2: Getting gmail.configuration model...')
            try:
                config_model = self.env['gmail.configuration']
                _logger.info(f'Config model object: {config_model}')
                _logger.info(f'Config model type: {type(config_model)}')
            except Exception as e:
                _logger.error(f'Error getting gmail.configuration model: {e}')
                return False
            
            # Check if method exists
            _logger.info('Step 3: Checking is_gmail_oauth_configured method...')
            if not hasattr(config_model, 'is_gmail_oauth_configured'):
                _logger.error('is_gmail_oauth_configured method not found')
                _logger.info(f'Available methods: {[attr for attr in dir(config_model) if not attr.startswith("_")][:10]}...')
                return False
            
            method = getattr(config_model, 'is_gmail_oauth_configured')
            _logger.info(f'Method object: {method}')
            _logger.info(f'Method type: {type(method)}')
            
            if method is None:
                _logger.error('is_gmail_oauth_configured method is None')
                return False
            
            if not callable(method):
                _logger.error(f'is_gmail_oauth_configured method is not callable: {type(method)}')
                return False
            
            # Call the method
            _logger.info('Step 4: Calling is_gmail_oauth_configured...')
            try:
                result = method()
                _logger.info(f'is_gmail_oauth_configured result: {result}')
                _logger.info(f'Result type: {type(result)}')
                _logger.info('=== _IS_SYSTEM_OAUTH_CONFIGURED COMPLETED ===')
                return result
            except Exception as e:
                _logger.error(f'Error calling is_gmail_oauth_configured: {e}', exc_info=True)
                return False
            
        except Exception as e:
            _logger.error(f'CRITICAL ERROR in _is_system_oauth_configured: {e}', exc_info=True)
            return False
    
    def _get_system_oauth_config(self):
        """Get system-level OAuth configuration - WITH COMPLETE DEBUG"""
        try:
            _logger.info('=== _GET_SYSTEM_OAUTH_CONFIG CALLED ===')
            
            # Default return value
            default_config = {
                'enabled': False,
                'client_id': '',
                'client_secret': '',
            }
            
            # Check if gmail.configuration model exists
            _logger.info('Step 1: Checking gmail.configuration model existence...')
            if 'gmail.configuration' not in self.env:
                _logger.error('gmail.configuration model not found in environment')
                return default_config
            
            _logger.info('gmail.configuration model found')
            
            # Get the model
            _logger.info('Step 2: Getting gmail.configuration model...')
            try:
                config_model = self.env['gmail.configuration']
                _logger.info(f'Config model object: {config_model}')
            except Exception as e:
                _logger.error(f'Error getting gmail.configuration model: {e}')
                return default_config
            
            # Check if method exists
            _logger.info('Step 3: Checking get_gmail_oauth_config method...')
            if not hasattr(config_model, 'get_gmail_oauth_config'):
                _logger.error('get_gmail_oauth_config method not found')
                return default_config
            
            method = getattr(config_model, 'get_gmail_oauth_config')
            _logger.info(f'Method object: {method}')
            _logger.info(f'Method type: {type(method)}')
            
            if method is None:
                _logger.error('get_gmail_oauth_config method is None')
                return default_config
            
            if not callable(method):
                _logger.error(f'get_gmail_oauth_config method is not callable: {type(method)}')
                return default_config
            
            # Call the method
            _logger.info('Step 4: Calling get_gmail_oauth_config...')
            try:
                result = method()
                _logger.info(f'get_gmail_oauth_config result: {result}')
                _logger.info(f'Result type: {type(result)}')
                _logger.info('=== _GET_SYSTEM_OAUTH_CONFIG COMPLETED ===')
                return result if result else default_config
            except Exception as e:
                _logger.error(f'Error calling get_gmail_oauth_config: {e}', exc_info=True)
                return default_config
            
        except Exception as e:
            _logger.error(f'CRITICAL ERROR in _get_system_oauth_config: {e}', exc_info=True)
            return {
                'enabled': False,
                'client_id': '',
                'client_secret': '',
            }
    
    def action_disconnect_gmail(self):
        """Disconnect Gmail account"""
        self.ensure_one()
        
        # Revoke tokens if possible
        if self.access_token:
            self._revoke_tokens()
        
        # Clear tokens and reset status
        self.write({
            'access_token': False,
            'refresh_token': False,
            'token_expires_at': False,
            'oauth_uid': False,
            'authorized_scopes': False,
            'last_oauth_date': False,
            'status': 'draft',
            'last_error_message': False,
            'history_id': False,
            'watch_expiration': False,
            'gmail_watch_active': False,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Disconnected'),
                'message': _('Gmail account has been disconnected.'),
                'type': 'success',
            }
        }
    
    def _get_gmail_service(self):
        """Get authenticated Gmail service using system OAuth config"""
        if not self.access_token:
            raise UserError(_('No access token available. Please connect Gmail first.'))
        
        # Check if token needs refresh
        if self.token_expires_at and self.token_expires_at <= datetime.now():
            self._refresh_token()
        
        try:
            # Get system OAuth config
            oauth_config = self._get_system_oauth_config()
            
            credentials = Credentials(
                token=self.access_token,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=oauth_config['client_id'],
                client_secret=oauth_config['client_secret']
            )
            
            service = build('gmail', 'v1', credentials=credentials)
            return service
            
        except Exception as e:
            _logger.error(f"Failed to create Gmail service for {self.email_address}: {e}")
            self.status = 'error'
            self.last_error_message = str(e)
            raise UserError(_('Failed to connect to Gmail: %s') % str(e))
    
    def _refresh_token(self):
        """Refresh OAuth access token using system OAuth config"""
        if not self.refresh_token:
            raise UserError(_('No refresh token available. Please reconnect Gmail.'))
        
        try:
            # Get system OAuth config
            oauth_config = self._get_system_oauth_config()
            
            token_url = 'https://oauth2.googleapis.com/token'
            
            token_data = {
                'client_id': oauth_config['client_id'],
                'client_secret': oauth_config['client_secret'],
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token',
            }
            
            response = requests.post(token_url, data=token_data, timeout=30)
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('error_description', f'HTTP {response.status_code}')
                raise UserError(_('Failed to refresh token: %s') % error_msg)
            
            token_response = response.json()
            
            # Update tokens
            self.write({
                'access_token': token_response.get('access_token'),
                'token_expires_at': datetime.now() + timedelta(seconds=int(token_response.get('expires_in', 3600))),
            })
            
            _logger.info(f"Token refreshed for {self.email_address}")
            
        except Exception as e:
            _logger.error(f"Token refresh failed for {self.email_address}: {e}")
            self.write({
                'status': 'expired',
                'last_error_message': str(e),
            })
            raise UserError(_('Failed to refresh token: %s') % str(e))
    
    def _revoke_tokens(self):
        """Revoke Google OAuth tokens"""
        try:
            revoke_url = f'https://oauth2.googleapis.com/revoke?token={self.access_token}'
            response = requests.post(revoke_url, timeout=10)
            
            if response.status_code == 200:
                _logger.info(f'Google tokens revoked for {self.email_address}')
            else:
                _logger.warning(f'Token revocation returned status {response.status_code}')
                
        except Exception as e:
            _logger.warning(f'Failed to revoke Google tokens for {self.email_address}: {str(e)}')
    
    # === ACCOUNT MANAGEMENT ACTIONS ===
    def action_test_connection(self):
        """Test Gmail API connection"""
        self.ensure_one()
        
        if not self.access_token:
            raise UserError(_('Please connect your Gmail account first.'))
        
        try:
            service = self._get_gmail_service()
            profile = service.users().getProfile(userId='me').execute()
            
            # Update account info
            self.write({
                'status': 'connected',
                'last_sync_date': fields.Datetime.now(),
                'last_error_message': False,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Test'),
                    'message': _('Gmail connection successful!'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            self.write({
                'status': 'error',
                'last_error_message': str(e),
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Test'),
                    'message': _('Connection failed: %s') % str(e),
                    'type': 'danger',
                }
            }
    
    def action_sync_now(self):
        """Trigger immediate email sync"""
        self.ensure_one()
        
        if self.status != 'connected':
            raise UserError(_('Gmail account must be connected to sync.'))
        
        try:
            # Use sync service for optimized sync
            sync_service = self.env['gmail.sync.service']
            sync_service.sync_account_emails(self.id)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sync Complete'),
                    'message': _('Email synchronization completed successfully.'),
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sync Failed'),
                    'message': _('Sync failed: %s') % str(e),
                    'type': 'danger',
                }
            }
    
    def action_share_account(self):
        """Open sharing wizard"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Share Gmail Account'),
            'res_model': 'gmail.account.share.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_account_id': self.id,
                'default_access_level': self.access_level,
                'default_shared_user_ids': [(6, 0, self.shared_user_ids.ids)],
            }
        }
    
    # === PUBSUB ACTION METHODS ===
    def action_setup_pubsub(self):
        """Setup complete Pub/Sub infrastructure"""
        self.ensure_one()
        
        try:
            self._setup_push_notifications()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Pub/Sub Setup Complete'),
                    'message': _('Push notifications have been configured successfully!'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Pub/Sub Setup Failed'),
                    'message': _('Setup failed: %s') % str(e),
                    'type': 'danger',
                }
            }
    
    def action_test_pubsub(self):
        """Test Pub/Sub configuration"""
        self.ensure_one()
        
        try:
            # Test publisher client
            publisher = self._get_pubsub_publisher_client()
            topic_path = publisher.topic_path(self.google_project_id, self.pubsub_topic_name)
            
            # Test topic exists
            topic = publisher.get_topic(request={"name": topic_path})
            
            # Test subscriber client
            subscriber = self._get_pubsub_subscriber_client()
            subscription_path = subscriber.subscription_path(
                self.google_project_id, 
                self.pubsub_subscription_name
            )
            
            # Test subscription exists
            subscription = subscriber.get_subscription(request={"subscription": subscription_path})
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Pub/Sub Test Successful'),
                    'message': _('All Pub/Sub components are working correctly!'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Pub/Sub Test Failed'),
                    'message': _('Test failed: %s') % str(e),
                    'type': 'danger',
                }
            }
    
    def action_renew_gmail_watch(self):
        """Renew Gmail watch (expires every 7 days)"""
        self.ensure_one()
        
        if not self.gmail_watch_active:
            raise UserError(_('Gmail watch is not currently active'))
        
        try:
            # Re-setup Gmail watch
            service = self._get_gmail_service()
            
            request_body = {
                'topicName': self.pubsub_topic,
                'labelIds': ['INBOX', 'SENT'],
                'labelFilterAction': 'include'
            }
            
            result = service.users().watch(userId='me', body=request_body).execute()
            
            # Update watch info
            self.write({
                'history_id': result.get('historyId'),
                'watch_expiration': datetime.fromtimestamp(int(result['expiration']) / 1000) if 'expiration' in result else False,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Gmail Watch Renewed'),
                    'message': _('Gmail watch has been renewed successfully!'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Gmail Watch Renewal Failed'),
                    'message': _('Renewal failed: %s') % str(e),
                    'type': 'danger',
                }
            }
    
    # === PUBSUB METHODS ===
    def _get_pubsub_publisher_client(self):
        """Get authenticated Pub/Sub publisher client"""
        self.ensure_one()
        
        if not self.service_account_key:
            raise UserError(_('Service account key not configured'))
        
        try:
            key_data = json.loads(self.service_account_key)
            credentials = service_account.Credentials.from_service_account_info(key_data)
            client = pubsub_v1.PublisherClient(credentials=credentials)
            return client
            
        except Exception as e:
            _logger.error(f'Failed to create Pub/Sub publisher client: {e}')
            raise UserError(_('Failed to create Pub/Sub client: %s') % str(e))
    
    def _get_pubsub_subscriber_client(self):
        """Get authenticated Pub/Sub subscriber client"""
        self.ensure_one()
        
        if not self.service_account_key:
            raise UserError(_('Service account key not configured'))
        
        try:
            key_data = json.loads(self.service_account_key)
            credentials = service_account.Credentials.from_service_account_info(key_data)
            client = pubsub_v1.SubscriberClient(credentials=credentials)
            return client
            
        except Exception as e:
            _logger.error(f'Failed to create Pub/Sub subscriber client: {e}')
            raise UserError(_('Failed to create Pub/Sub client: %s') % str(e))
    
    def _setup_push_notifications(self):
        """Complete Pub/Sub and Gmail watch setup"""
        self.ensure_one()
        
        if not self.google_project_id:
            raise UserError(_('Google Cloud Project ID is required for push notifications'))
        
        if not self.service_account_key:
            raise UserError(_('Service account key is required for Pub/Sub access'))
        
        try:
            # Ensure Pub/Sub topic exists
            self._ensure_pubsub_topic_exists()
            
            # Ensure push subscription exists  
            self._ensure_pubsub_subscription_exists()
            
            # Setup Gmail watch
            service = self._get_gmail_service()
            
            request_body = {
                'topicName': self.pubsub_topic,
                'labelIds': ['INBOX', 'SENT'],
                'labelFilterAction': 'include'
            }
            
            result = service.users().watch(userId='me', body=request_body).execute()
            
            # Store watch info
            self.write({
                'history_id': result.get('historyId'),
                'watch_expiration': datetime.fromtimestamp(int(result['expiration']) / 1000) if 'expiration' in result else False,
                'gmail_watch_active': True,
            })
            
            _logger.info(f'Complete push notifications setup successful for {self.email_address}')
            return True
            
        except Exception as e:
            _logger.error(f'Push notifications setup failed for {self.email_address}: {e}')
            self.write({
                'gmail_watch_active': False,
                'last_error_message': str(e),
            })
            raise UserError(_('Failed to setup push notifications: %s') % str(e))
    
    def _ensure_pubsub_topic_exists(self):
        """Create Pub/Sub topic if it doesn't exist"""
        self.ensure_one()
        
        if not self.google_project_id or not self.pubsub_topic_name:
            raise UserError(_('Google Project ID and topic name are required'))
        
        try:
            publisher = self._get_pubsub_publisher_client()
            topic_path = publisher.topic_path(self.google_project_id, self.pubsub_topic_name)
            
            try:
                publisher.get_topic(request={"name": topic_path})
                _logger.info(f'Pub/Sub topic already exists: {topic_path}')
                
            except NotFound:
                topic = publisher.create_topic(request={"name": topic_path})
                _logger.info(f'Created Pub/Sub topic: {topic.name}')
            
            self.pubsub_topic_created = True
            
        except Exception as e:
            _logger.error(f'Failed to ensure Pub/Sub topic exists: {e}')
            raise UserError(_('Failed to create Pub/Sub topic: %s') % str(e))
    
    def _ensure_pubsub_subscription_exists(self):
        """Create push subscription if it doesn't exist"""
        self.ensure_one()
        
        if not self.google_project_id or not self.pubsub_topic_name or not self.pubsub_subscription_name:
            raise UserError(_('Project ID, topic name, and subscription name are required'))
        
        try:
            subscriber = self._get_pubsub_subscriber_client()
            publisher = self._get_pubsub_publisher_client()
            
            subscription_path = subscriber.subscription_path(
                self.google_project_id, 
                self.pubsub_subscription_name
            )
            topic_path = publisher.topic_path(self.google_project_id, self.pubsub_topic_name)
            
            webhook_url = self._get_webhook_url()
            
            try:
                subscriber.get_subscription(request={"subscription": subscription_path})
                _logger.info(f'Pub/Sub subscription already exists: {subscription_path}')
                
            except NotFound:
                push_config = pubsub_v1.PushConfig(push_endpoint=webhook_url)
                
                subscription = subscriber.create_subscription(
                    request={
                        "name": subscription_path,
                        "topic": topic_path,
                        "push_config": push_config,
                    }
                )
                _logger.info(f'Created Pub/Sub subscription: {subscription.name}')
            
            self.pubsub_subscription_created = True
            
        except Exception as e:
            _logger.error(f'Failed to ensure Pub/Sub subscription exists: {e}')
            raise UserError(_('Failed to create Pub/Sub subscription: %s') % str(e))
    
    def _get_webhook_url(self):
        """Get webhook URL for push notifications"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f'{base_url}/gmail/webhook/pubsub'
    
    # === EMAIL SENDING ===
    def send_email(self, to_emails, subject, body_html, body_plain=None, cc_emails=None, bcc_emails=None, attachments=None):
        """Send email via Gmail API with enhanced attachment support"""
        self.ensure_one()
        
        if self.status != 'connected':
            raise UserError(_('Gmail account is not connected.'))
        
        try:
            service = self._get_gmail_service()
            
            # Create message
            message = MIMEMultipart()
            message['To'] = ', '.join(to_emails) if isinstance(to_emails, list) else to_emails
            message['Subject'] = subject
            message['From'] = self.email_address
            
            if cc_emails:
                message['Cc'] = ', '.join(cc_emails) if isinstance(cc_emails, list) else cc_emails
            if bcc_emails:
                message['Bcc'] = ', '.join(bcc_emails) if isinstance(bcc_emails, list) else bcc_emails
            
            # Add body
            if body_plain:
                message.attach(MIMEText(body_plain, 'plain'))
            if body_html:
                message.attach(MIMEText(body_html, 'html'))
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(base64.b64decode(attachment['data']))
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment["filename"]}'
                    )
                    message.attach(part)
            
            # Send message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            _logger.info(f"Email sent successfully via {self.email_address}: {send_message['id']}")
            return send_message['id']
            
        except Exception as e:
            _logger.error(f"Failed to send email via {self.email_address}: {e}")
            raise UserError(_('Failed to send email: %s') % str(e))
    
    # === CRON METHODS ===
    @api.model
    def cron_sync_emails(self):
        """Cron job to sync emails for all connected accounts"""
        accounts = self.search([
            ('status', '=', 'connected'),
            ('sync_enabled', '=', True),
            ('sync_frequency', '!=', 'manual')
        ])
        
        for account in accounts:
            try:
                account._sync_emails()
            except Exception as e:
                _logger.error(f'Cron sync failed for {account.email_address}: {str(e)}')
                continue
    
    @api.model
    def cron_refresh_expiring_tokens(self):
        """Refresh tokens that will expire soon"""
        expiring_soon = self.search([
            ('status', '=', 'connected'),
            ('token_expires_at', '<=', datetime.now() + timedelta(hours=1))
        ])
        
        for account in expiring_soon:
            try:
                account._refresh_token()
            except Exception as e:
                _logger.error(f"Token refresh failed for {account.email_address}: {e}")
                account.status = 'expired'
    
    @api.model
    def cron_renew_gmail_watches(self):
        """Auto-renew Gmail watches that will expire soon"""
        expiring_soon = self.search([
            ('gmail_watch_active', '=', True),
            ('watch_expiration', '<=', datetime.now() + timedelta(days=1))
        ])
        
        for account in expiring_soon:
            try:
                account.action_renew_gmail_watch()
                _logger.info(f"Auto-renewed Gmail watch for {account.email_address}")
            except Exception as e:
                _logger.error(f"Auto-renewal failed for {account.email_address}: {e}")
                account.gmail_watch_active = False
    
    def _sync_emails(self):
        """Internal method to sync emails using sync service"""
        self.ensure_one()
        
        if self.status != 'connected':
            raise UserError(_('Gmail account is not connected.'))
        
        try:
            sync_service = self.env['gmail.sync.service']
            sync_service.sync_account_emails(self.id)
            
            _logger.info(f'Email sync completed for {self.email_address}')
            
        except Exception as e:
            _logger.error(f'Email sync failed for {self.email_address}: {e}')
            self.last_error_message = str(e)
            raise UserError(_('Email sync failed: %s') % str(e))
    
    def _process_gmail_notification(self, history_id):
        """Process Gmail push notification for real-time sync"""
        self.ensure_one()
        
        try:
            sync_service = self.env['gmail.sync.service']
            sync_service.process_pubsub_notification(self.id, history_id)
            
            _logger.info(f'Gmail notification processed for {self.email_address}')
            
        except Exception as e:
            _logger.error(f'Gmail notification processing failed for {self.email_address}: {e}')
            raise
    
    # === UTILITY METHODS ===
    @api.model
    def get_user_accounts(self, user_id=None):
        """Get Gmail accounts accessible by a user"""
        if not user_id:
            user_id = self.env.user.id
        
        return self.search([
            '|', '|', '|',
            ('user_id', '=', user_id),
            '&', ('access_level', '=', 'shared'), ('shared_user_ids', 'in', [user_id]),
            '&', ('access_level', '=', 'company'), ('user_id.company_id', '=', self.env.user.company_id.id),
            ('access_level', '=', 'company')
        ])
    
    @api.model
    def create_user_account(self, email_address, account_name=None):
        """Create a new Gmail account for current user"""
        if not account_name:
            account_name = email_address.split('@')[0].title()
        
        return self.create({
            'name': account_name,
            'email_address': email_address,
            'user_id': self.env.user.id,
            'access_level': 'private',
            'status': 'oauth_required',
        })
