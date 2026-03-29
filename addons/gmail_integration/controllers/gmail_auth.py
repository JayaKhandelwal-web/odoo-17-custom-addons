# -*- coding: utf-8 -*-

import json
import logging
import secrets
from werkzeug.exceptions import BadRequest
from werkzeug.urls import url_encode
from werkzeug.utils import redirect
from datetime import datetime, timedelta

from odoo import http, _, fields
from odoo.http import request
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)


class GmailAuthController(http.Controller):
    """
    Gmail Auth Controller with Database State Storage - FIXED VERSION
    """

    @http.route('/gmail/auth', type='http', auth='user', methods=['GET'], website=True)
    def gmail_auth_start(self, **kwargs):
        """Start Gmail OAuth 2.0 authorization flow - FIXED VERSION"""
        try:
            _logger.info('=== Gmail Auth Start Called ===')
            
            account_id = kwargs.get('account_id')
            if not account_id:
                return request.render('gmail_integration.auth_error', {
                    'error_message': _('Missing account ID parameter')
                })
            
            # Get Gmail account
            account = request.env['gmail.account'].browse(int(account_id))
            if not account.exists():
                return request.render('gmail_integration.auth_error', {
                    'error_message': _('Gmail account not found')
                })
            
            # Check user has access to this account
            if not account._check_access_rights('write'):
                return request.render('gmail_integration.auth_error', {
                    'error_message': _('You do not have permission to configure this Gmail account')
                })
            
            # Get system OAuth configuration
            oauth_config = self._get_system_oauth_config()
            if not oauth_config['enabled'] or not oauth_config['client_id'] or not oauth_config['client_secret']:
                return request.render('gmail_integration.auth_error', {
                    'error_message': _(
                        'Gmail OAuth is not configured at system level. '
                        'Please contact your administrator to configure Gmail integration.'
                    )
                })
            
            # Generate state parameter for security
            state = secrets.token_urlsafe(32)
            
            # FIXED: Store state in database instead of session
            self._store_oauth_state(state, account_id, request.env.user.id)
            
            _logger.info(f'OAuth state stored in database - State: {state}, Account: {account_id}, User: {request.env.user.id}')
            
            # Gmail OAuth 2.0 authorization URL using shared OAuth app
            auth_params = {
                'client_id': oauth_config['client_id'],
                'redirect_uri': self._get_redirect_uri(),
                'scope': self._get_gmail_scopes(),
                'response_type': 'code',
                'access_type': 'offline',
                'prompt': 'consent',
                'state': state,
                'login_hint': account.email_address,
            }
            
            auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + url_encode(auth_params)
            
            _logger.info(f'Redirecting to Google OAuth for account {account.email_address}')
            
            return redirect(auth_url)
            
        except Exception as e:
            _logger.error(f'Gmail auth start error: {str(e)}')
            return request.render('gmail_integration.auth_error', {
                'error_message': _('Failed to start authorization: %s') % str(e)
            })
    
    @http.route('/gmail/auth/callback', type='http', auth='user', methods=['GET'], website=True)
    def gmail_auth_callback(self, **kwargs):
        """Handle Gmail OAuth 2.0 callback - FIXED VERSION"""
        try:
            _logger.info('=== Gmail Auth Callback ===')
            
            # Get state from URL parameters
            state = kwargs.get('state')
            _logger.info(f'State from Google: {state}')
            
            # FIXED: Retrieve state from database instead of session
            oauth_data = self._get_oauth_state(state)
            
            _logger.info(f'OAuth data from database: {oauth_data}')
            
            # Validate state parameter
            if not state or not oauth_data:
                _logger.error('State validation failed - no matching oauth data found')
                return request.render('gmail_integration.auth_error', {
                    'error_message': _('State validation failed. Please try again.')
                })
            
            account_id = oauth_data.get('account_id')
            user_id = oauth_data.get('user_id')
            
            if not account_id:
                _logger.error('No account ID in oauth data')
                return request.render('gmail_integration.auth_error', {
                    'error_message': _('Session expired. Please try again.')
                })
            
            # Security check - ensure same user
            if user_id != request.env.user.id:
                _logger.error(f'User mismatch - stored: {user_id}, current: {request.env.user.id}')
                return request.render('gmail_integration.auth_error', {
                    'error_message': _('User validation failed. Please try again.')
                })
            
            # Check for authorization errors
            error = kwargs.get('error')
            if error:
                error_description = kwargs.get('error_description', error)
                _logger.warning(f'Gmail OAuth error: {error} - {error_description}')
                
                # Clean up stored state
                self._cleanup_oauth_state(state)
                
                return request.render('gmail_integration.auth_error', {
                    'error_message': _('Authorization failed: %s') % error_description
                })
            
            # Get authorization code
            auth_code = kwargs.get('code')
            if not auth_code:
                self._cleanup_oauth_state(state)
                return request.render('gmail_integration.auth_error', {
                    'error_message': _('Authorization code not received')
                })
            
            # Get Gmail account and verify access
            account = request.env['gmail.account'].browse(int(account_id))
            if not account.exists():
                self._cleanup_oauth_state(state)
                return request.render('gmail_integration.auth_error', {
                    'error_message': _('Gmail account not found')
                })
            
            if not account._check_access_rights('write'):
                self._cleanup_oauth_state(state)
                return request.render('gmail_integration.auth_error', {
                    'error_message': _('You do not have permission to configure this Gmail account')
                })
            
            # Exchange authorization code for tokens
            token_data = self._exchange_code_for_tokens(auth_code)
            
            # Get user info
            user_info = self._get_user_info(token_data.get('access_token'))
            
            # Store tokens in account
            account.sudo().write({
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'token_expires_at': self._calculate_token_expiry(token_data.get('expires_in')),
                'oauth_uid': user_info.get('id'),
                'authorized_scopes': token_data.get('scope', self._get_gmail_scopes()),
                'last_oauth_date': fields.Datetime.now(),
                'status': 'connected',
                'last_error_message': False,
            })
            
            # Clean up stored state
            self._cleanup_oauth_state(state)
            
            _logger.info(f'Gmail OAuth completed successfully for {account.email_address}')
            
            return request.render('gmail_integration.auth_success', {
                'account': account,
                'user_info': user_info,
                'message': _('Gmail account connected successfully using shared OAuth!')
            })
            
        except Exception as e:
            # Clean up state on error
            if 'state' in locals():
                self._cleanup_oauth_state(state)
            
            _logger.error(f'Gmail auth callback error: {str(e)}')
            return request.render('gmail_integration.auth_error', {
                'error_message': _('Authorization failed: %s') % str(e)
            })
    
    # === DATABASE STATE STORAGE METHODS ===
    
    def _store_oauth_state(self, state, account_id, user_id):
        """Store OAuth state in database with expiration"""
        try:
            # Clean up old expired states first
            self._cleanup_expired_states()
            
            # Store new state in ir.config_parameter (temporary storage)
            state_data = {
                'account_id': account_id,
                'user_id': user_id,
                'created_at': fields.Datetime.now().isoformat(),
                'expires_at': (fields.Datetime.now() + timedelta(minutes=10)).isoformat()
            }
            
            param_name = f'gmail_oauth_state_{state}'
            request.env['ir.config_parameter'].sudo().set_param(
                param_name, 
                json.dumps(state_data)
            )
            
            _logger.info(f'OAuth state stored: {param_name}')
            
        except Exception as e:
            _logger.error(f'Failed to store OAuth state: {e}')
            raise UserError(_('Failed to store authorization state'))
    
    def _get_oauth_state(self, state):
        """Retrieve OAuth state from database"""
        try:
            if not state:
                return None
            
            param_name = f'gmail_oauth_state_{state}'
            state_json = request.env['ir.config_parameter'].sudo().get_param(param_name)
            
            if not state_json:
                _logger.warning(f'OAuth state not found: {param_name}')
                return None
            
            state_data = json.loads(state_json)
            
            # Check if expired
            expires_at = datetime.fromisoformat(state_data['expires_at'])
            if datetime.now() > expires_at:
                _logger.warning(f'OAuth state expired: {param_name}')
                self._cleanup_oauth_state(state)
                return None
            
            _logger.info(f'OAuth state retrieved: {param_name}')
            return state_data
            
        except Exception as e:
            _logger.error(f'Failed to retrieve OAuth state: {e}')
            return None
    
    def _cleanup_oauth_state(self, state):
        """Remove specific OAuth state from database"""
        try:
            if not state:
                return
            
            param_name = f'gmail_oauth_state_{state}'
            request.env['ir.config_parameter'].sudo().set_param(param_name, False)
            _logger.info(f'OAuth state cleaned up: {param_name}')
            
        except Exception as e:
            _logger.error(f'Failed to cleanup OAuth state: {e}')
    
    def _cleanup_expired_states(self):
        """Clean up expired OAuth states from database"""
        try:
            # Get all Gmail OAuth state parameters
            params = request.env['ir.config_parameter'].sudo().search([
                ('key', 'like', 'gmail_oauth_state_%')
            ])
            
            cleaned_count = 0
            for param in params:
                try:
                    if param.value and param.value != 'False':
                        state_data = json.loads(param.value)
                        expires_at = datetime.fromisoformat(state_data['expires_at'])
                        
                        if datetime.now() > expires_at:
                            param.sudo().unlink()
                            cleaned_count += 1
                except:
                    # If we can't parse it, it's probably corrupted, so remove it
                    param.sudo().unlink()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                _logger.info(f'Cleaned up {cleaned_count} expired OAuth states')
                
        except Exception as e:
            _logger.error(f'Failed to cleanup expired OAuth states: {e}')
    
    # === EXISTING METHODS ===
    
    @http.route('/gmail/auth/disconnect', type='http', auth='user', methods=['POST'], csrf=True)
    def gmail_auth_disconnect(self, **kwargs):
        """Disconnect Gmail account"""
        try:
            account_id = kwargs.get('account_id')
            if not account_id:
                raise UserError(_('Missing account ID'))
            
            account = request.env['gmail.account'].browse(int(account_id))
            if not account.exists():
                raise UserError(_('Gmail account not found'))
            
            # Check permissions
            if not account._check_access_rights('write'):
                raise UserError(_('You do not have permission to disconnect this account'))
            
            # Revoke tokens with Google
            if account.access_token:
                self._revoke_google_tokens(account.access_token)
            
            # Clear account tokens
            account.sudo().write({
                'access_token': False,
                'refresh_token': False,
                'token_expires_at': False,
                'oauth_uid': False,
                'authorized_scopes': False,
                'last_oauth_date': False,
                'status': 'draft',
                'last_error_message': False,
            })
            
            _logger.info(f'Gmail account disconnected: {account.email_address}')
            
            return request.redirect('/web#action=gmail_integration.action_gmail_account_user')
            
        except Exception as e:
            _logger.error(f'Gmail disconnect error: {str(e)}')
            raise UserError(_('Failed to disconnect account: %s') % str(e))
    
    @http.route('/gmail/auth/test', type='json', auth='user', methods=['POST'])
    def gmail_auth_test(self, account_id):
        """Test Gmail API connection"""
        try:
            account = request.env['gmail.account'].browse(account_id)
            if not account.exists():
                return {'success': False, 'error': _('Account not found')}
            
            if not account._check_access_rights('read'):
                return {'success': False, 'error': _('Access denied')}
            
            if not account.access_token:
                return {'success': False, 'error': _('Account not connected')}
            
            # Test Gmail API connection
            success, error_msg = self._test_gmail_connection(account)
            
            if success:
                account.sudo().write({
                    'status': 'connected',
                    'last_sync_date': fields.Datetime.now(),
                    'last_error_message': False,
                })
                return {'success': True, 'message': _('Connection successful')}
            else:
                account.sudo().write({
                    'status': 'error',
                    'last_error_message': error_msg,
                })
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            _logger.error(f'Gmail connection test error: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    @http.route('/gmail/auth/refresh', type='json', auth='user', methods=['POST'])
    def gmail_auth_refresh(self, account_id):
        """Refresh Gmail access token"""
        try:
            account = request.env['gmail.account'].browse(account_id)
            if not account.exists():
                return {'success': False, 'error': _('Account not found')}
            
            if not account._check_access_rights('write'):
                return {'success': False, 'error': _('Access denied')}
            
            if not account.refresh_token:
                return {'success': False, 'error': _('No refresh token available')}
            
            # Refresh token using system OAuth config
            token_data = self._refresh_access_token(account)
            
            # Update account
            account.sudo().write({
                'access_token': token_data.get('access_token'),
                'token_expires_at': self._calculate_token_expiry(token_data.get('expires_in')),
                'status': 'connected',
                'last_error_message': False,
            })
            
            return {'success': True, 'message': _('Token refreshed successfully')}
            
        except Exception as e:
            _logger.error(f'Gmail token refresh error: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    @http.route('/gmail/auth/status', type='json', auth='user', methods=['POST'])
    def gmail_auth_status(self, account_id):
        """Get Gmail authentication status"""
        try:
            account = request.env['gmail.account'].browse(account_id)
            if not account.exists():
                return {'success': False, 'error': _('Account not found')}
            
            if not account._check_access_rights('read'):
                return {'success': False, 'error': _('Access denied')}
            
            status_info = {
                'success': True,
                'status': account.status,
                'email_address': account.email_address,
                'owner': account.user_id.name,
                'access_level': account.access_level,
                'last_sync_date': account.last_sync_date.isoformat() if account.last_sync_date else None,
                'last_oauth_date': account.last_oauth_date.isoformat() if account.last_oauth_date else None,
                'has_access_token': bool(account.access_token),
                'has_refresh_token': bool(account.refresh_token),
                'token_expires_at': account.token_expires_at.isoformat() if account.token_expires_at else None,
                'last_error_message': account.last_error_message,
                'authorized_scopes': account.authorized_scopes,
                'quota_usage': {
                    'used': account.daily_quota_used,
                    'limit': account.daily_quota_limit,
                    'percentage': account.quota_percentage,
                },
                'message_stats': {
                    'total': account.total_messages,
                    'unread': account.unread_messages,
                },
                'system_oauth_configured': self._is_system_oauth_configured(),
            }
            
            return status_info
            
        except Exception as e:
            _logger.error(f'Gmail status check error: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    @http.route('/gmail/auth/setup_guide', type='http', auth='user', methods=['GET'], website=True)
    def gmail_setup_guide(self):
        """Display Gmail OAuth setup guide"""
        oauth_config = self._get_system_oauth_config()
        
        return request.render('gmail_integration.setup_guide', {
            'redirect_uri': self._get_redirect_uri(),
            'required_scopes': self._get_gmail_scopes(),
            'system_configured': oauth_config['enabled'] and oauth_config['client_id'],
            'client_id': oauth_config.get('client_id', 'Not configured'),
        })
    
    @http.route('/gmail/auth/privacy_policy', type='http', auth='public', methods=['GET'], website=True)
    def gmail_privacy_policy(self):
        """Display privacy policy for Gmail integration"""
        return request.render('gmail_integration.privacy_policy', {
            'company_name': request.env.company.name,
            'scopes_used': self._get_gmail_scopes().split(' '),
        })
    
    # === HELPER METHODS ===
    
    def _get_system_oauth_config(self):
        """Get system-level OAuth configuration"""
        try:
            return request.env['gmail.configuration'].get_gmail_oauth_config()
        except Exception as e:
            _logger.error(f'Error getting system OAuth config: {e}')
            return {
                'enabled': False,
                'client_id': '',
                'client_secret': '',
            }
    
    def _is_system_oauth_configured(self):
        """Check if system OAuth is configured"""
        try:
            return request.env['gmail.configuration'].is_gmail_oauth_configured()
        except Exception as e:
            _logger.error(f'Error checking system OAuth config: {e}')
            return False
    
    def _get_redirect_uri(self):
        """Get OAuth redirect URI"""
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f'{base_url}/gmail/auth/callback'
    
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
    
    def _exchange_code_for_tokens(self, auth_code):
        """Exchange authorization code for tokens using system OAuth config"""
        import requests
        
        oauth_config = self._get_system_oauth_config()
        
        if not oauth_config.get('enabled'):
            raise UserError(_('Gmail OAuth is disabled at system level'))
        
        if not oauth_config.get('client_id') or not oauth_config.get('client_secret'):
            raise UserError(_('System OAuth configuration is incomplete'))
        
        token_url = 'https://oauth2.googleapis.com/token'
        
        token_data = {
            'client_id': oauth_config['client_id'],
            'client_secret': oauth_config['client_secret'],
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': self._get_redirect_uri(),
        }
        
        _logger.info(f'Exchanging OAuth code using shared client_id: {oauth_config["client_id"][:20]}...')
        
        response = requests.post(token_url, data=token_data, timeout=30)
        
        if response.status_code != 200:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_msg = error_data.get('error_description', f'HTTP {response.status_code}')
            
            if 'invalid_grant' in error_msg:
                error_msg = 'Authorization code is invalid or expired. Please try again.'
            elif 'invalid_client' in error_msg:
                error_msg = 'Invalid shared OAuth configuration. Please check system settings.'
            elif 'redirect_uri_mismatch' in error_msg:
                error_msg = f'Redirect URI mismatch. Expected: {self._get_redirect_uri()}'
            
            _logger.error(f'OAuth token exchange failed: {error_msg}')
            raise UserError(_('Failed to exchange authorization code: %s') % error_msg)
        
        token_response = response.json()
        _logger.info('Successfully received OAuth tokens using shared configuration')
        
        return token_response
    
    def _refresh_access_token(self, account):
        """Refresh access token using shared OAuth config"""
        import requests
        
        oauth_config = self._get_system_oauth_config()
        
        token_url = 'https://oauth2.googleapis.com/token'
        
        token_data = {
            'client_id': oauth_config['client_id'],
            'client_secret': oauth_config['client_secret'],
            'refresh_token': account.refresh_token,
            'grant_type': 'refresh_token',
        }
        
        response = requests.post(token_url, data=token_data, timeout=30)
        
        if response.status_code != 200:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_msg = error_data.get('error_description', f'HTTP {response.status_code}')
            raise UserError(_('Failed to refresh token: %s') % error_msg)
        
        return response.json()
    
    def _get_user_info(self, access_token):
        """Get user info from Google OAuth"""
        import requests
        
        try:
            userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = requests.get(userinfo_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_info = response.json()
                return user_info
            else:
                _logger.warning(f'Failed to get user info: HTTP {response.status_code}')
                return {}
                
        except Exception as e:
            _logger.warning(f'Error getting user info: {e}')
            return {}
    
    def _revoke_google_tokens(self, access_token):
        """Revoke Google OAuth tokens"""
        try:
            import requests
            
            revoke_url = f'https://oauth2.googleapis.com/revoke?token={access_token}'
            response = requests.post(revoke_url, timeout=10)
            
            if response.status_code == 200:
                _logger.info('Google tokens revoked successfully')
            else:
                _logger.warning(f'Token revocation returned status {response.status_code}')
                
        except Exception as e:
            _logger.warning(f'Failed to revoke Google tokens: {str(e)}')
    
    def _test_gmail_connection(self, account):
        """Test Gmail API connection using shared OAuth config"""
        try:
            if not account.access_token:
                return False, _('No access token')
            
            # Check if token is expired
            if account.token_expires_at and account.token_expires_at < fields.Datetime.now():
                return False, _('Access token expired')
            
            # Get shared OAuth config for testing
            oauth_config = self._get_system_oauth_config()
            
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            credentials = Credentials(
                token=account.access_token,
                refresh_token=account.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=oauth_config['client_id'],
                client_secret=oauth_config['client_secret'],
            )
            
            service = build('gmail', 'v1', credentials=credentials)
            
            # Make test API call
            profile = service.users().getProfile(userId='me').execute()
            
            if profile.get('emailAddress'):
                return True, None
            else:
                return False, _('Invalid API response')
            
        except Exception as e:
            return False, str(e)
    
    def _calculate_token_expiry(self, expires_in):
        """Calculate token expiry datetime"""
        if not expires_in:
            return False
        
        return datetime.now() + timedelta(seconds=int(expires_in))
