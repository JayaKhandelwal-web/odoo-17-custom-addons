import requests
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class MyOperatorConfig(models.Model):
    _name = 'myoperator.config'
    _description = 'MyOperator Configuration'
    _rec_name = 'name'

    name = fields.Char('Configuration Name', required=True, default='MyOperator Config')
    api_token = fields.Char('API Token', required=True, help='MyOperator API Token')
    base_url = fields.Char('Base URL', required=True,
                           default='https://developers.myoperator.co',
                           help='MyOperator API Base URL')
    active = fields.Boolean('Active', default=True)
    auto_sync_enabled = fields.Boolean('Auto Sync Enabled', default=True,
                                       help='Enable automatic sync of call logs')
    sync_interval = fields.Integer('Sync Interval (minutes)', default=15,
                                   help='Interval for automatic sync in minutes')
    webhook_url = fields.Char('Webhook URL', readonly=False,
                              help='URL for MyOperator webhooks')
    last_sync_date = fields.Datetime('Last Sync Date', readonly=True)
    connection_status = fields.Selection([
        ('not_tested', 'Not Tested'),
        ('connected', 'Connected'),
        ('failed', 'Connection Failed')
    ], string='Connection Status', default='not_tested', readonly=True)

    # Callback functionality settings
    enable_callback = fields.Boolean('Enable Callback', default=True,
                                     help='Enable callback functionality')
    callback_method = fields.Selection([
        ('browser', 'Browser Click-to-Call (Recommended)'),
        ('api', 'API Integration (if available)'),
        ('notification', 'Notification Only'),
    ], string='Callback Method', default='browser',
        help='Method to use for callbacks')
    callback_source_number = fields.Char('Callback Source Number',
                                         help='Your MyOperator number to use for callbacks')

    @api.model
    def create(self, vals):
        # Ensure only one active configuration
        if vals.get('active', True):
            self.search([('active', '=', True)]).write({'active': False})
        return super().create(vals)

    def write(self, vals):
        if vals.get('active', False):
            self.search([('active', '=', True), ('id', '!=', self.id)]).write({'active': False})
        return super().write(vals)

    @api.model
    def get_active_config(self):
        """Get the active MyOperator configuration"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            raise UserError(_('No active MyOperator configuration found. Please configure MyOperator first.'))
        return config

    def test_connection(self):
        """Test connection to MyOperator API"""
        try:
            url = f"{self.base_url}/user"
            params = {'token': self.api_token}

            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    self.connection_status = 'connected'
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Success'),
                            'message': _('Connection to MyOperator API successful!'),
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                else:
                    self.connection_status = 'failed'
                    raise ValidationError(_('API returned error: %s') % data.get('message', 'Unknown error'))
            else:
                self.connection_status = 'failed'
                raise ValidationError(_('API request failed with status code: %s') % response.status_code)

        except requests.exceptions.RequestException as e:
            self.connection_status = 'failed'
            raise ValidationError(_('Connection failed: %s') % str(e))

    def _make_api_request(self, endpoint, method='GET', data=None, params=None):
        """Make API request to MyOperator"""
        if not params:
            params = {}

        url = f"{self.base_url}/{endpoint}"

        try:
            # Different authentication methods for different endpoints
            if endpoint == 'search':
                # For search endpoint, token MUST be in request body (not query params)
                if not data:
                    data = {}
                data['token'] = self.api_token

                # Use JSON format for search endpoint
                headers = {'Content-Type': 'application/json'}
                response = requests.post(url, json=data, headers=headers, timeout=30)

            else:
                # For other endpoints, use query parameter
                params['token'] = self.api_token

                if method == 'GET':
                    response = requests.get(url, params=params, timeout=30)
                elif method == 'POST':
                    response = requests.post(url, params=params, json=data, timeout=30)
                elif method == 'PUT':
                    response = requests.put(url, params=params, json=data, timeout=30)
                elif method == 'DELETE':
                    response = requests.delete(url, params=params, timeout=30)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f"MyOperator API request failed: {response.status_code} - {response.text}")
                return {'status': 'error', 'message': f'API request failed: {response.status_code}',
                        'response': response.text}

        except Exception as e:
            _logger.error(f"MyOperator API request exception: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def make_callback(self, destination_number):
        """Initiate a callback through available methods"""
        if not self.enable_callback:
            return {'status': 'error', 'message': 'Callback functionality is disabled'}

        # Clean the destination number
        clean_destination = destination_number.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')',
                                                                                                                  '')

        try:
            if self.callback_method == 'api':
                # Try different possible API endpoints for callbacks
                return self._try_api_callback(clean_destination)
            elif self.callback_method == 'browser':
                # Return browser-based callback URL
                return self._generate_browser_callback(clean_destination)
            else:
                # Default: notification method
                return self._notification_callback(clean_destination)

        except Exception as e:
            _logger.error(f"Callback exception: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _try_api_callback(self, destination_number):
        """Try different API endpoints for callback"""
        # List of possible endpoints MyOperator might use
        endpoints_to_try = [
            'call',  # Common endpoint name
            'click2call',  # Based on their click-to-call feature
            'initiate_call',  # Another common name
            'outbound',  # Based on their outbound service
            'make_call',  # Simple endpoint name
        ]

        for endpoint in endpoints_to_try:
            try:
                # Try different parameter combinations
                data_variations = [
                    {
                        'to': destination_number,
                        'from': self.callback_source_number,
                    },
                    {
                        'destination': destination_number,
                        'source': self.callback_source_number,
                    },
                    {
                        'called_number': destination_number,
                        'caller_number': self.callback_source_number,
                    },
                    {
                        'number': destination_number,
                    }
                ]

                for data in data_variations:
                    result = self._make_api_request(endpoint, method='POST', data=data)
                    if result.get('status') == 'success':
                        _logger.info(f"Callback successful using endpoint: {endpoint} with data: {data}")
                        return {'status': 'success', 'message': 'Callback initiated successfully'}

            except Exception as e:
                _logger.debug(f"Endpoint {endpoint} failed: {str(e)}")
                continue

        # If all API attempts fail, fall back to notification
        _logger.warning("All API callback attempts failed, falling back to notification method")
        return self._notification_callback(destination_number)

    def _generate_browser_callback(self, destination_number):
        """Generate a browser-based callback URL"""
        # MyOperator webcall URL format based on your screenshot
        callback_url = f"https://in.app.myoperator.com/webcall?number={destination_number}"

        return {
            'status': 'success',
            'message': f'Opening MyOperator webcall for {destination_number}',
            'callback_url': callback_url,
            'method': 'browser'
        }

    def _notification_callback(self, destination_number):
        """Provide notification-based callback (fallback method)"""
        return {
            'status': 'success',
            'message': f'Please manually call {destination_number} using MyOperator',
            'destination': destination_number,
            'source': self.callback_source_number,
            'method': 'notification'
        }

    def sync_users(self):
        """Sync users from MyOperator"""
        result = self._make_api_request('user')

        if result.get('status') == 'success' and 'data' in result:
            users_data = result['data']
            MyOperatorUser = self.env['myoperator.user']

            for user_data in users_data:
                existing_user = MyOperatorUser.search([
                    ('user_id', '=', user_data.get('user_id')),
                    ('config_id', '=', self.id)
                ], limit=1)

                vals = {
                    'config_id': self.id,
                    'user_id': user_data.get('user_id'),
                    'name': user_data.get('name'),
                    'email': user_data.get('email'),
                    'company_id_mo': user_data.get('company_id'),
                    'uuid': user_data.get('uuid'),
                }

                if existing_user:
                    existing_user.write(vals)
                else:
                    MyOperatorUser.create(vals)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Users synced successfully!'),
                    'type': 'success',
                }
            }
        else:
            raise UserError(_('Failed to sync users: %s') % result.get('message', 'Unknown error'))

    def sync_call_logs(self, date_from=None, date_to=None, limit=100):
        """Sync call logs from MyOperator"""
        # Prepare the data payload for search endpoint
        search_data = {
            'page_size': limit,
        }

        # Add date filters if provided
        if date_from:
            search_data['date_from'] = date_from
        if date_to:
            search_data['date_to'] = date_to

        result = self._make_api_request('search', method='POST', data=search_data)

        if result.get('status') == 'success' and 'data' in result:
            # Parse the response structure based on your test results
            if 'hits' in result['data']:
                logs_data = result['data']['hits']
                MyOperatorCallLog = self.env['myoperator.call.log']

                synced_count = 0
                for hit in logs_data:
                    log_data = hit.get('_source', {})

                    # Extract call ID from different possible fields
                    call_id = hit.get('_id') or log_data.get('unique_id') or hit.get('user_id')

                    if not call_id:
                        continue

                    existing_log = MyOperatorCallLog.search([
                        ('call_id', '=', call_id),
                        ('config_id', '=', self.id)
                    ], limit=1)

                    if not existing_log:
                        # Map the response fields to our model fields
                        vals = {
                            'config_id': self.id,
                            'call_id': call_id,
                            'caller_number': log_data.get('caller_number'),
                            'called_number': log_data.get('called_number') or log_data.get('_did'),
                            'call_type': self._map_call_type(log_data.get('type'), log_data.get('event')),
                            'duration': self._parse_duration(log_data.get('duration')),
                            'timestamp': self._parse_timestamp(log_data.get('start_time')),
                            'status': self._map_call_status(log_data.get('status')),
                            'recording_url': log_data.get('fileurl'),
                        }
                        MyOperatorCallLog.create(vals)
                        synced_count += 1

                self.last_sync_date = fields.Datetime.now()

                return {
                    'synced_count': synced_count,
                    'total_logs': len(logs_data)
                }
            else:
                # Handle different response structure
                return {
                    'synced_count': 0,
                    'total_logs': 0
                }
        else:
            error_msg = result.get('message', 'Unknown error')
            if result.get('response'):
                error_msg += f". Response: {result.get('response')}"
            raise UserError(_('Failed to sync call logs: %s') % error_msg)

    def _map_call_type(self, type_val, event_val):
        """Map MyOperator type and event to our call_type"""
        if type_val == 1:  # Call
            if event_val == 1:
                return 'inbound'
            elif event_val == 2:
                return 'outbound'
        return 'internal'

    def _map_call_status(self, status_val):
        """Map MyOperator status to our status"""
        status_map = {
            1: 'answered',
            2: 'missed',
            3: 'busy',
            4: 'failed'
        }
        return status_map.get(status_val, 'missed')

    def _parse_duration(self, duration_str):
        """Parse duration from MM:SS format to seconds"""
        if not duration_str:
            return 0
        try:
            if ':' in duration_str:
                parts = duration_str.split(':')
                if len(parts) == 3:  # HH:MM:SS
                    hours, minutes, seconds = map(int, parts)
                    return hours * 3600 + minutes * 60 + seconds
                elif len(parts) == 2:  # MM:SS
                    minutes, seconds = map(int, parts)
                    return minutes * 60 + seconds
            return int(duration_str)
        except:
            return 0

    def _parse_timestamp(self, timestamp_val):
        """Parse timestamp from various formats"""
        if not timestamp_val:
            return False
        try:
            from datetime import datetime
            # If it's a Unix timestamp
            if isinstance(timestamp_val, (int, float)):
                return datetime.fromtimestamp(timestamp_val)
            # If it's a string, try to parse it
            elif isinstance(timestamp_val, str):
                return datetime.strptime(timestamp_val, '%Y-%m-%d %H:%M:%S')
            return timestamp_val
        except:
            return False

    def test_search_endpoint(self):
        """Test the search endpoint specifically"""
        try:
            # Test with minimal data
            test_data = {
                'page_size': 5,
                'type': 'call'
            }

            result = self._make_api_request('search', method='POST', data=test_data)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Search Test Result'),
                    'message': _('Search endpoint test: %s') % result.get('message', str(result)),
                    'type': 'info',
                    'sticky': True,
                }
            }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Search Test Failed'),
                    'message': _('Error: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    @api.model
    def cron_sync_call_logs(self):
        """Cron job to sync call logs automatically"""
        active_configs = self.search([('active', '=', True), ('auto_sync_enabled', '=', True)])

        for config in active_configs:
            try:
                config.sync_call_logs()
                _logger.info(f"Auto sync completed for config: {config.name}")
            except Exception as e:
                _logger.error(f"Auto sync failed for config {config.name}: {str(e)}")