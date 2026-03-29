# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from werkzeug.urls import url_encode
import logging
import requests
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class GmailOAuthWizard(models.TransientModel):
    _name = 'gmail.oauth.wizard'
    _description = 'Gmail OAuth Authorization Wizard - Shared OAuth Version'

    # Related Gmail Account
    account_id = fields.Many2one(
        'gmail.account',
        string='Gmail Account',
        required=True,
        readonly=True,
        help="Gmail account to authorize"
    )
    
    account_name = fields.Char(
        string='Account Name',
        related='account_id.name',
        readonly=True
    )
    
    email_address = fields.Char(
        string='Email Address',
        related='account_id.email_address',
        readonly=True
    )
    
    # System OAuth Configuration Display (Fixed to use gmail.configuration)
    system_oauth_configured = fields.Boolean(
        string='System OAuth Configured',
        compute='_compute_system_oauth_config',
        help="Whether system-level OAuth is configured"
    )
    
    client_id = fields.Char(
        string='Client ID (System)',
        compute='_compute_system_oauth_config',
        readonly=True,
        help="System-level OAuth Client ID"
    )
    
    redirect_uri = fields.Char(
        string='Redirect URI',
        compute='_compute_redirect_uri',
        readonly=True,
        help="OAuth redirect URI for Google Cloud Console configuration"
    )
    
    # OAuth Authorization
    auth_url = fields.Text(
        string='Authorization URL',
        compute='_compute_auth_url',
        readonly=True,
        help="Copy this URL and open it in your browser"
    )
    
    authorization_code = fields.Text(
        string='Authorization Code',
        help="Paste the authorization code from Google here"
    )
    
    # Wizard States
    state = fields.Selection([
        ('step1', 'Step 1: Get Authorization Code'),
        ('step2', 'Step 2: Verify Code'),
        ('step3', 'Authorization Complete'),
    ], string='Wizard State', default='step1')
    
    # Status and Messages
    status_message = fields.Text(
        string='Status Message',
        readonly=True,
        help="Current status of the authorization process"
    )
    
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
        help="Error details if authorization fails"
    )
    
    # Success Indicators
    is_authorized = fields.Boolean(
        string='Authorization Successful',
        default=False,
        readonly=True
    )
    
    token_info = fields.Text(
        string='Token Information',
        readonly=True,
        help="Details about received tokens (for debugging)"
    )
    
    # System Configuration Warning
    config_warning = fields.Text(
        string='Configuration Warning',
        compute='_compute_system_oauth_config',
        help="Warning if system OAuth is not configured"
    )
    
    @api.depends('account_id')
    def _compute_system_oauth_config(self):
        """Get system-level OAuth configuration - FIXED to use gmail.configuration"""
        for record in self:
            try:
                # FIXED: Use gmail.configuration instead of res.config.settings
                oauth_config = record.env['gmail.configuration'].get_gmail_oauth_config()
                
                record.system_oauth_configured = (
                    oauth_config.get('enabled', False) and 
                    oauth_config.get('client_id') and 
                    oauth_config.get('client_secret')
                )
                
                if record.system_oauth_configured:
                    record.client_id = oauth_config.get('client_id', '')
                    record.config_warning = False
                else:
                    record.client_id = 'Not configured at system level'
                    record.config_warning = _(
                        'Gmail OAuth is not configured at system level.\n\n'
                        'Please ask your administrator to configure Gmail integration '
                        'in Gmail Settings (Gmail Integration menu).'
                    )
                    
            except Exception as e:
                _logger.error(f'Error loading Gmail OAuth configuration: {e}')
                record.system_oauth_configured = False
                record.client_id = 'Error loading configuration'
                record.config_warning = _('Error loading OAuth configuration: %s') % str(e)
    
    @api.depends('account_id')
    def _compute_redirect_uri(self):
        """Compute OAuth redirect URI"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.redirect_uri = f"{base_url}/gmail/auth/callback"
    
    @api.depends('account_id', 'system_oauth_configured', 'client_id')
    def _compute_auth_url(self):
        """Generate Google OAuth authorization URL using system config"""
        for record in self:
            if not record.account_id:
                record.auth_url = "No account selected"
                continue
                
            if not record.system_oauth_configured:
                record.auth_url = "System OAuth not configured - contact administrator"
                continue
                
            try:
                # OAuth parameters using system config
                auth_params = {
                    'client_id': record.client_id,
                    'redirect_uri': record.redirect_uri,
                    'scope': record._get_gmail_scopes(),
                    'response_type': 'code',
                    'access_type': 'offline',
                    'prompt': 'consent',
                    'state': f'manual_wizard_{record.account_id.id}_{record.env.user.id}',
                    'login_hint': record.email_address,  # Suggest the target email
                }
                
                auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + url_encode(auth_params)
                record.auth_url = auth_url
                
            except Exception as e:
                record.auth_url = f"Error generating URL: {str(e)}"
    
    def _get_gmail_scopes(self):
        """Get required Gmail API scopes"""
        scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/gmail.compose',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
        ]
        return ' '.join(scopes)
    
    @api.model
    def default_get(self, fields_list):
        """Set default values when wizard opens"""
        res = super().default_get(fields_list)
        
        # Get account from context
        account_id = self._context.get('active_id')
        if account_id and self._context.get('active_model') == 'gmail.account':
            res['account_id'] = account_id
            
            # Set initial status message
            account = self.env['gmail.account'].browse(account_id)
            
            # Check if user has access to this account
            if not account._check_access_rights('write'):
                res['status_message'] = _(
                    'Access Denied: You do not have permission to configure this Gmail account.\n\n'
                    'Only the account owner or users with shared access can perform OAuth authorization.'
                )
                res['state'] = 'step1'  # Keep in step1 but show error
            else:
                res['status_message'] = _(
                    'Ready to authorize Gmail account: %s\n\n'
                    'This wizard uses the system-wide OAuth configuration.\n'
                    'Follow the steps below to complete authorization.'
                ) % account.email_address
        
        return res
    
    @api.constrains('authorization_code')
    def _check_authorization_code(self):
        """Validate authorization code format"""
        for record in self:
            if record.authorization_code:
                # Basic validation - Google auth codes are typically alphanumeric
                code = record.authorization_code.strip()
                if len(code) < 10:
                    raise ValidationError(_('Authorization code seems too short. Please check and try again.'))
    
    def action_open_auth_url(self):
        """Open authorization URL in new browser tab"""
        self.ensure_one()
        
        if not self.system_oauth_configured:
            raise UserError(_(
                'System OAuth not configured.\n\n'
                'Please ask your administrator to configure Gmail integration '
                'in Gmail Settings (Gmail Integration menu).'
            ))
        
        if not self.auth_url or self.auth_url.startswith('Error') or self.auth_url.startswith('System'):
            raise UserError(_('Cannot generate authorization URL. Please check system OAuth configuration.'))
        
        # Update status
        self.status_message = _(
            'Authorization URL opened in new tab.\n\n'
            'Please:\n'
            '1. Complete authorization in the new tab\n'
            '2. Copy the authorization code from the result\n'
            '3. Paste it in the field below\n'
            '4. Click "Verify Authorization Code"\n\n'
            'Note: This uses the system-wide OAuth app configured by your administrator.'
        )
        
        return {
            'type': 'ir.actions.act_url',
            'url': self.auth_url,
            'target': 'new',
        }
    
    def action_copy_auth_url(self):
        """Copy authorization URL to clipboard (via notification)"""
        self.ensure_one()
        
        if not self.system_oauth_configured:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Configuration Required'),
                    'message': _('System OAuth not configured. Contact your administrator.'),
                    'type': 'danger',
                }
            }
        
        if not self.auth_url or self.auth_url.startswith('Error'):
            raise UserError(_('Cannot generate authorization URL. Please check system OAuth configuration.'))
        
        # Update status with URL
        self.status_message = _(
            'Copy the URL below and open it in your browser:\n\n'
            '%s\n\n'
            'After authorization, copy the code and paste it in the Authorization Code field.'
        ) % self.auth_url
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Authorization URL Ready'),
                'message': _('Authorization URL is displayed below. Copy and open it in your browser.'),
                'type': 'info',
                'sticky': True,
            }
        }
    
    def action_verify_code(self):
        """Verify authorization code and exchange for tokens using system OAuth"""
        self.ensure_one()
        
        if not self.authorization_code:
            raise UserError(_('Please enter the authorization code first.'))
        
        if not self.account_id:
            raise UserError(_('Gmail account not found.'))
        
        if not self.system_oauth_configured:
            raise UserError(_(
                'System OAuth not configured.\n\n'
                'Please ask your administrator to configure Gmail integration first.'
            ))
        
        # Check user has access to this account
        if not self.account_id._check_access_rights('write'):
            raise UserError(_('You do not have permission to configure this Gmail account.'))
        
        try:
            # Update status
            self.status_message = _('Verifying authorization code using system OAuth configuration...')
            self.error_message = False
            
            # Clean authorization code
            auth_code = self.authorization_code.strip()
            
            # Exchange code for tokens using system OAuth config
            token_data = self._exchange_code_for_tokens(auth_code)
            
            # Get user info to verify email
            user_info = self._get_user_info(token_data.get('access_token'))
            
            # Verify email matches (optional security check)
            if user_info.get('email') and user_info['email'].lower() != self.account_id.email_address.lower():
                _logger.warning(f'Email mismatch during OAuth: expected {self.account_id.email_address}, got {user_info.get("email")}')
                # Note: We could make this stricter by raising an error, but for now just log it
            
            # Store tokens in Gmail account
            self.account_id.sudo().write({
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'token_expires_at': self._calculate_token_expiry(token_data.get('expires_in')),
                'oauth_uid': user_info.get('id'),
                'authorized_scopes': token_data.get('scope', self._get_gmail_scopes()),
                'last_oauth_date': fields.Datetime.now(),
                'status': 'connected',
                'last_error_message': False,
            })
            
            # Update wizard state
            self.write({
                'state': 'step3',
                'is_authorized': True,
                'status_message': _(
                    'Authorization completed successfully!\n\n'
                    'Gmail account "%(account)s" is now connected using the system OAuth configuration.\n'
                    'Account owner: %(owner)s\n'
                    'Authorized email: %(email)s\n\n'
                    'You can now sync emails and send messages through this account.'
                ) % {
                    'account': self.account_id.display_name,
                    'owner': self.account_id.user_id.name,
                    'email': user_info.get('email', 'Not available')
                },
                'token_info': self._format_token_info(token_data, user_info),
                'error_message': False,
            })
            
            _logger.info(f'Gmail OAuth completed successfully for account {self.account_id.email_address} via wizard (user: {self.env.user.name})')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Authorization Successful'),
                    'message': _('Gmail account connected successfully using shared OAuth!'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            _logger.error(f'Gmail OAuth wizard error for account {self.account_id.email_address}: {error_msg}')
            
            # Update wizard with error
            self.write({
                'error_message': error_msg,
                'status_message': _(
                    'Authorization failed.\n\n'
                    'Please check the error message below and try again.\n'
                    'Make sure you copied the complete authorization code.\n\n'
                    'Common issues:\n'
                    '• Authorization code expired (get a new one)\n'
                    '• Incomplete code copied\n'
                    '• System OAuth configuration issue'
                ),
                'is_authorized': False,
            })
            
            # Update account status
            self.account_id.sudo().write({
                'status': 'error',
                'last_error_message': error_msg,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Authorization Failed'),
                    'message': _('Authorization failed: %s') % error_msg,
                    'type': 'danger',
                }
            }
    
    def _exchange_code_for_tokens(self, auth_code):
        """Exchange authorization code for access and refresh tokens using system OAuth config"""
        # FIXED: Get system OAuth configuration from gmail.configuration
        oauth_config = self.env['gmail.configuration'].get_gmail_oauth_config()
        
        if not oauth_config.get('enabled'):
            raise UserError(_('Gmail OAuth is disabled at system level'))
        
        if not oauth_config.get('client_id') or not oauth_config.get('client_secret'):
            raise UserError(_('System OAuth configuration is incomplete - missing Client ID or Secret'))
        
        token_url = 'https://oauth2.googleapis.com/token'
        
        token_data = {
            'client_id': oauth_config['client_id'],
            'client_secret': oauth_config['client_secret'],
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
        }
        
        _logger.info(f'Exchanging OAuth code for tokens using client_id: {oauth_config["client_id"][:20]}...')
        
        response = requests.post(token_url, data=token_data, timeout=30)
        
        if response.status_code != 200:
            # Parse error response
            try:
                error_data = response.json()
                error_msg = error_data.get('error_description', error_data.get('error', f'HTTP {response.status_code}'))
                
                # Provide more helpful error messages
                if 'invalid_grant' in error_msg:
                    error_msg = 'Authorization code is invalid or expired. Please get a new authorization code.'
                elif 'invalid_client' in error_msg:
                    error_msg = 'Invalid OAuth client configuration. Please check system OAuth settings.'
                elif 'redirect_uri_mismatch' in error_msg:
                    error_msg = f'Redirect URI mismatch. Expected: {self.redirect_uri}'
                    
            except:
                error_msg = f'HTTP {response.status_code}: {response.text[:200]}'
            
            raise UserError(_('Failed to exchange authorization code: %s') % error_msg)
        
        token_response = response.json()
        _logger.info(f'Successfully received OAuth tokens for {self.account_id.email_address}')
        
        return token_response
    
    def _get_user_info(self, access_token):
        """Get user info from Google OAuth"""
        try:
            userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = requests.get(userinfo_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_info = response.json()
                _logger.info(f'Retrieved user info: {user_info.get("email", "unknown")}')
                return user_info
            else:
                _logger.warning(f'Failed to get user info: HTTP {response.status_code}')
                return {}
                
        except Exception as e:
            _logger.warning(f'Error getting user info: {e}')
            return {}
    
    def _calculate_token_expiry(self, expires_in):
        """Calculate token expiry datetime"""
        if not expires_in:
            return False
        
        return datetime.now() + timedelta(seconds=int(expires_in))
    
    def _format_token_info(self, token_data, user_info=None):
        """Format token information for display"""
        info = []
        
        if token_data.get('access_token'):
            info.append(f"✅ Access Token: Received ({len(token_data['access_token'])} chars)")
        
        if token_data.get('refresh_token'):
            info.append(f"✅ Refresh Token: Received ({len(token_data['refresh_token'])} chars)")
        
        if token_data.get('expires_in'):
            expiry = self._calculate_token_expiry(token_data['expires_in'])
            info.append(f"⏰ Token Expires: {expiry.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if token_data.get('scope'):
            info.append(f"🔐 Granted Scopes: {token_data['scope']}")
        
        if user_info:
            if user_info.get('email'):
                info.append(f"📧 Authorized Email: {user_info['email']}")
            if user_info.get('name'):
                info.append(f"👤 Account Name: {user_info['name']}")
            if user_info.get('id'):
                info.append(f"🆔 Google User ID: {user_info['id']}")
        
        info.append(f"🏢 OAuth Method: System-wide shared OAuth app")
        info.append(f"👤 Configured by: {self.env.user.name}")
        
        return '\n'.join(info) if info else 'Token information not available'
    
    def action_test_connection(self):
        """Test Gmail connection after authorization"""
        self.ensure_one()
        
        if not self.is_authorized:
            raise UserError(_('Please complete authorization first.'))
        
        try:
            # Use account's test connection method
            result = self.account_id.action_test_connection()
            
            # Update wizard status
            self.status_message = _(
                'Connection test completed successfully!\n\n'
                'Your Gmail account is properly configured and ready to use.\n'
                'You can close this wizard and start using Gmail integration.\n\n'
                'Next steps:\n'
                '• Configure sync settings if needed\n'
                '• Set up push notifications for real-time updates\n'
                '• Configure sharing if this account should be accessible to other users'
            )
            
            return result
            
        except Exception as e:
            self.error_message = str(e)
            self.status_message = _(
                'Connection test failed.\n\n'
                'The authorization was successful, but there may be an issue '
                'with the Gmail API connection. Please check the error message below.'
            )
            raise
    
    def action_close_wizard(self):
        """Close wizard and return to Gmail accounts"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gmail.account',
            'view_mode': 'tree,form',
            'name': _('Gmail Accounts'),
            'target': 'current',
        }
    
    def action_open_account(self):
        """Open the Gmail account form"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gmail.account',
            'res_id': self.account_id.id,
            'view_mode': 'form',
            'name': _('Gmail Account'),
            'target': 'current',
        }
    
    def action_restart_authorization(self):
        """Restart the authorization process"""
        self.ensure_one()
        
        # Reset wizard state
        self.write({
            'state': 'step1',
            'authorization_code': False,
            'is_authorized': False,
            'error_message': False,
            'token_info': False,
            'status_message': _(
                'Authorization process restarted.\n\n'
                'Click "Open Authorization URL" to begin the process again using the system OAuth configuration.'
            ),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Authorization Restarted'),
                'message': _('You can now start the authorization process again.'),
                'type': 'info',
            }
        }
    
    def action_open_system_settings(self):
        """Open system settings for OAuth configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Gmail Integration Settings'),
            'res_model': 'gmail.configuration',
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'}
        }
    
    def action_refresh_config(self):
        """Refresh system OAuth configuration (force recompute)"""
        self.ensure_one()
        
        # Force recompute of OAuth config fields
        self._compute_system_oauth_config()
        self._compute_auth_url()
        
        if self.system_oauth_configured:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Configuration Refreshed'),
                    'message': _('System OAuth configuration has been refreshed successfully.'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Configuration Not Ready'),
                    'message': _('System OAuth is still not configured. Please contact your administrator.'),
                    'type': 'warning',
                }
            }
