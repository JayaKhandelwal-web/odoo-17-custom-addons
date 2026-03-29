from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class InteraktConfig(models.Model):
    _name = 'interakt.config'
    _description = 'Interakt WhatsApp Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Configuration Name', required=True, default='Interakt Config')
    api_key = fields.Char(string='API Key', required=True, tracking=True,
                          help='Your Interakt API Key (Basic Auth format)')
    base_url = fields.Char(string='Base URL', required=True,
                           default='https://api.interakt.ai/v1',
                           tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    # Test Configuration
    test_phone = fields.Char(string='Test Phone Number',
                             help='Phone number for testing (without country code)')
    test_country_code = fields.Char(string='Test Country Code',
                                    default='+91',
                                    help='Country code for test number')

    # Statistics
    total_messages_sent = fields.Integer(string='Total Messages Sent',
                                         compute='_compute_statistics',
                                         store=False)
    successful_messages = fields.Integer(string='Successful Messages',
                                         compute='_compute_statistics',
                                         store=False)
    failed_messages = fields.Integer(string='Failed Messages',
                                     compute='_compute_statistics',
                                     store=False)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    _sql_constraints = [
        ('active_unique',
         'CHECK(1=1)',
         'Only one active configuration is allowed!')
    ]

    @api.constrains('active')
    def _check_active_config(self):
        """Ensure only one active configuration exists"""
        for record in self:
            if record.active:
                other_active = self.search([
                    ('active', '=', True),
                    ('id', '!=', record.id)
                ])
                if other_active:
                    raise ValidationError(_(
                        'Only one Interakt configuration can be active at a time. '
                        'Please deactivate the other configuration first.'
                    ))

    def _compute_statistics(self):
        """Compute message statistics"""
        for config in self:
            logs = self.env['interakt.message.log'].search([
                ('config_id', '=', config.id)
            ])
            config.total_messages_sent = len(logs)
            config.successful_messages = len(logs.filtered(lambda l: l.status == 'sent'))
            config.failed_messages = len(logs.filtered(lambda l: l.status == 'failed'))

    @api.model
    def get_active_config(self):
        """Get the active Interakt configuration"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            raise UserError(_(
                'No active Interakt configuration found. '
                'Please configure Interakt settings first.'
            ))
        return config

    def _get_headers(self):
        """Get request headers with authorization"""
        self.ensure_one()
        return {
            "Authorization": f"Basic {self.api_key}",
            "Content-Type": "application/json"
        }

    def test_connection(self):
        """Test the Interakt API connection"""
        self.ensure_one()

        if not self.test_phone:
            raise UserError(_('Please provide a test phone number.'))

        try:
            # Try to create/update a test user
            url = f"{self.base_url}/public/track/users/"
            headers = self._get_headers()

            payload = {
                "phoneNumber": self.test_phone,
                "countryCode": self.test_country_code,
                "userId": f"test_user_{self.id}",
                "traits": {
                    "name": "Test User"
                }
            }

            response = requests.post(url, headers=headers, json=payload, timeout=10)

            if response.ok:
                self.message_post(
                    body=_('✅ Connection test successful! API is working correctly.'),
                    message_type='notification'
                )
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Connection test successful!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_msg = response.text
                _logger.error(f"Interakt connection test failed: {error_msg}")
                raise UserError(_(
                    'Connection test failed!\n'
                    'Status Code: %s\n'
                    'Error: %s'
                ) % (response.status_code, error_msg))

        except requests.exceptions.RequestException as e:
            _logger.error(f"Interakt connection test error: {str(e)}")
            raise UserError(_(
                'Connection test failed!\n'
                'Error: %s\n\n'
                'Please check your API key and network connection.'
            ) % str(e))

    def create_or_update_user(self, phone, country_code, user_name, user_id=None):
        """Create or update user in Interakt"""
        self.ensure_one()

        url = f"{self.base_url}/public/track/users/"
        headers = self._get_headers()

        if not user_id:
            user_id = f"{user_name.lower().replace(' ', '_')}_{phone}"

        payload = {
            "phoneNumber": phone,
            "countryCode": country_code,
            "userId": user_id,
            "traits": {
                "name": user_name
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)

            if response.ok:
                _logger.info(f"User created/updated in Interakt: {user_name} ({phone})")
                return True
            else:
                _logger.error(f"Failed to create/update user in Interakt: {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Error creating/updating user in Interakt: {str(e)}")
            return False

    def send_template_message(self, phone, country_code, template_name,
                              body_values=None, header_url=None, callback_data=None):
        """
        Send a WhatsApp template message

        Args:
            phone: Phone number without country code
            country_code: Country code with + (e.g., "+91")
            template_name: Name of the template in Interakt
            body_values: List of values for template variables
            header_url: URL for header image/video/document
            callback_data: Optional callback data for tracking

        Returns:
            dict: Response with status and message_id or error
        """
        self.ensure_one()

        url = f"{self.base_url}/public/message/"
        headers = self._get_headers()

        # Build template data
        template_data = {
            "name": template_name,
            "languageCode": "en"
        }

        # Add header if provided
        if header_url:
            template_data['headerValues'] = [header_url]

        # Add body values if provided
        if body_values:
            template_data['bodyValues'] = body_values

        # Build message payload
        payload = {
            "countryCode": country_code,
            "phoneNumber": phone,
            "callbackData": callback_data or f"{template_name}_message",
            "type": "Template",
            "template": template_data
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)

            if response.ok:
                result = response.json()
                _logger.info(f"Template message sent successfully: {template_name} to {phone}")
                return {
                    'status': 'success',
                    'message_id': result.get('id', 'Unknown'),
                    'response': result
                }
            else:
                error_msg = response.text
                _logger.error(f"Failed to send template message: {error_msg}")
                return {
                    'status': 'error',
                    'message': error_msg,
                    'status_code': response.status_code
                }

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Error sending template message: {error_msg}")
            return {
                'status': 'error',
                'message': error_msg
            }

    def action_view_message_logs(self):
        """View message logs for this configuration"""
        self.ensure_one()
        return {
            'name': _('Message Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'interakt.message.log',
            'view_mode': 'tree,form',
            'domain': [('config_id', '=', self.id)],
            'context': {'default_config_id': self.id},
        }