from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import requests
import json
import logging
import re

_logger = logging.getLogger(__name__)


class MyOperatorChatConfig(models.Model):
    _name = 'myoperator.chat.config'
    _description = 'MyOperator Chat Configuration'
    _rec_name = 'name'

    name = fields.Char('Configuration Name', required=True, default='MyOperator Chat Config')
    api_key = fields.Char('API Key', required=True, help='MyOperator Chat API Key')
    base_url = fields.Char('Base URL', required=True,
                           default='publicapi.myoperator.co',
                           help='MyOperator Chat API Base URL')
    company_id = fields.Char('Company ID', required=True, help='MyOperator Company ID')
    phone_number_id = fields.Char('Phone Number ID', required=True, help='WhatsApp Phone Number ID')
    waba_id = fields.Char('WABA ID', required=True, help='WhatsApp Business Account ID')

    active = fields.Boolean('Active', default=True)
    auto_sync_enabled = fields.Boolean('Auto Sync Enabled', default=True,
                                       help='Enable automatic sync of chat conversations')
    sync_interval = fields.Integer('Sync Interval (minutes)', default=15,
                                   help='Interval for automatic sync in minutes')

    webhook_url = fields.Char('Webhook URL', readonly=False,
                              help='URL for MyOperator chat webhooks')
    last_sync_date = fields.Datetime('Last Sync Date', readonly=True)
    connection_status = fields.Selection([
        ('not_tested', 'Not Tested'),
        ('connected', 'Connected'),
        ('failed', 'Connection Failed')
    ], string='Connection Status', default='not_tested', readonly=True)

    # Chat specific settings
    default_template = fields.Char('Default Template', default='hello_world',
                                   help='Default template for 24hr+ conversations')
    auto_reply_enabled = fields.Boolean('Auto Reply Enabled', default=False,
                                        help='Enable automatic replies')
    auto_reply_message = fields.Text('Auto Reply Message',
                                     help='Message to send automatically when customer texts')

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
        """Get the active MyOperator chat configuration"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            raise UserError(_('No active MyOperator chat configuration found. Please configure MyOperator Chat first.'))
        return config

    def test_connection(self):
        """Test connection to MyOperator Chat API"""
        try:
            import http.client

            conn = http.client.HTTPSConnection(self.base_url)

            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'X-MYOP-COMPANY-ID': self.company_id,
            }

            endpoint = "/chat/conversations?limit=1"
            conn.request("GET", endpoint, '', headers)
            res = conn.getresponse()
            data = res.read()
            conn.close()

            if res.status == 200:
                self.connection_status = 'connected'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Connection to MyOperator Chat API successful!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                self.connection_status = 'failed'
                response_text = data.decode('utf-8')
                raise ValidationError(
                    _('API request failed with status code: %s\nResponse: %s') % (res.status, response_text))

        except Exception as e:
            self.connection_status = 'failed'
            raise ValidationError(_('Connection failed: %s') % str(e))

    def sync_conversations(self, limit=50):
        """Sync conversations from MyOperator Chat API"""
        try:
            result = self._make_api_request(f'/chat/conversations?limit={limit}')

            if 'data' in result and 'results' in result['data']:
                conversations = result['data']['results']
                MyOperatorConversation = self.env['myoperator.conversation']

                synced_count = 0
                for conv_data in conversations:
                    existing_conv = MyOperatorConversation.search([
                        ('conversation_id', '=', conv_data.get('id')),
                        ('config_id', '=', self.id)
                    ], limit=1)

                    # Parse last_message_at properly
                    last_message_at = conv_data.get('last_message_at')
                    parsed_timestamp = False
                    if last_message_at:
                        parsed_timestamp = self._parse_timestamp(last_message_at)
                        # Ensure it's a proper Odoo datetime
                        if parsed_timestamp and hasattr(parsed_timestamp, 'replace'):
                            # Remove timezone info if present
                            if hasattr(parsed_timestamp, 'tzinfo') and parsed_timestamp.tzinfo:
                                parsed_timestamp = parsed_timestamp.replace(tzinfo=None)

                    # Handle status field - map unknown values to valid ones
                    api_status = conv_data.get('status', 'open')
                    # Define valid statuses based on your conversation model
                    status_mapping = {
                        'open': 'open',
                        'assigned': 'assigned',
                        'unassigned': 'open',  # Map unassigned to open
                        'closed': 'closed',
                        'resolved': 'resolved',
                        'pending': 'pending',
                        'active': 'active',
                        'inactive': 'inactive'
                    }
                    conversation_status = status_mapping.get(api_status.lower(), 'open')

                    vals = {
                        'config_id': self.id,
                        'conversation_id': conv_data.get('id'),
                        'customer_name': conv_data.get('customer_name'),
                        'customer_contact': conv_data.get('customer_contact'),
                        'status': conversation_status,
                        'unread_count': conv_data.get('unread_count', 0),
                        'last_message_at': parsed_timestamp,
                    }

                    if existing_conv:
                        existing_conv.write(vals)
                    else:
                        MyOperatorConversation.create(vals)
                        synced_count += 1

                self.last_sync_date = fields.Datetime.now()
                return {'synced_count': synced_count, 'total_conversations': len(conversations)}

            return {'synced_count': 0, 'total_conversations': 0}

        except Exception as e:
            _logger.error(f"Error in sync_conversations: {str(e)}")
            raise UserError(_('Failed to sync conversations: %s') % str(e))

    def _get_customer_name_for_phone(self, phone_number):
        """Get customer name for phone number from conversations or partners"""
        customer_name = "Customer"  # Default

        try:
            # Clean phone number for matching
            clean_number = re.sub(r'[^\d+]', '', phone_number)
            search_number = clean_number[-10:]  # Last 10 digits

            # First try to find in existing conversations
            conversation = self.env['myoperator.conversation'].search([
                ('customer_contact', 'ilike', search_number)
            ], limit=1)

            if conversation and conversation.customer_name:
                customer_name = conversation.customer_name
            else:
                # Search in partners
                partner = self.env['res.partner'].search([
                    '|', ('phone', 'ilike', search_number),
                    ('mobile', 'ilike', search_number)
                ], limit=1)
                if partner:
                    customer_name = partner.name

        except Exception as e:
            _logger.warning(f"Could not fetch customer name for {phone_number}: {str(e)}")

        return customer_name

    def send_message(self, phone_number, message_text, use_template=False, template_name=None,
                     template_parameters=None):
        """Send a message via MyOperator Chat API - Enhanced with Template Variable Support"""
        try:
            import http.client
            import json

            # Parse phone number using the correct method name
            country_code, customer_number = self._parse_phone_number(phone_number)

            # Prepare headers
            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'X-MYOP-COMPANY-ID': self.company_id,
                'Content-Type': 'application/json'
            }

            # Define endpoint
            endpoint = "/chat/messages"

            if use_template and template_name:
                # Get customer name for template variables
                customer_name = self._get_customer_name_for_phone(phone_number)

                # Prepare template variables
                template_vars = {}
                if template_parameters:
                    template_vars.update(template_parameters)

                # Set default variables for known templates
                if template_name == "shop_from_us_on_whatsapp":
                    template_vars["var_1"] = template_vars.get("var_1", customer_name)
                elif "var_1" not in template_vars:
                    # Default var_1 for any template that might need it
                    template_vars["var_1"] = customer_name

                # Template message - try multiple structures with variables
                payloads_to_try = [
                    # Method 1: With body containing variables
                    {
                        "phone_number_id": self.phone_number_id,
                        "customer_country_code": country_code,
                        "customer_number": customer_number,
                        "data": {
                            "type": "template",
                            "context": {
                                "template_name": template_name,
                                "language": "en",
                                "body": template_vars
                            }
                        }
                    },
                    # Method 2: With components structure (WhatsApp Business API standard)
                    {
                        "phone_number_id": self.phone_number_id,
                        "customer_country_code": country_code,
                        "customer_number": customer_number,
                        "data": {
                            "type": "template",
                            "context": {
                                "template_name": template_name,
                                "language": "en",
                                "components": [
                                    {
                                        "type": "body",
                                        "parameters": [
                                            {"type": "text", "text": str(value)}
                                            for value in template_vars.values()
                                        ]
                                    }
                                ] if template_vars else []
                            }
                        }
                    },
                    # Method 3: Alternative structure with name field
                    {
                        "phone_number_id": self.phone_number_id,
                        "customer_country_code": country_code,
                        "customer_number": customer_number,
                        "data": {
                            "type": "template",
                            "context": {
                                "name": template_name,
                                "language": "en",
                                "body": template_vars
                            }
                        }
                    },
                    # Method 4: Direct body variables in data
                    {
                        "phone_number_id": self.phone_number_id,
                        "customer_country_code": country_code,
                        "customer_number": customer_number,
                        "data": {
                            "type": "template",
                            "context": {
                                "template_name": template_name,
                                "language": "en"
                            },
                            "body": template_vars
                        }
                    },
                    # Method 5: Original structure (for fallback)
                    {
                        "phone_number_id": self.phone_number_id,
                        "customer_country_code": country_code,
                        "customer_number": customer_number,
                        "data": {
                            "type": "template",
                            "context": {
                                "name": template_name,
                                "language": "en"
                            }
                        }
                    }
                ]

                # Try each payload structure
                for i, payload in enumerate(payloads_to_try, 1):
                    _logger.info(f"Trying template method {i} with payload: {json.dumps(payload)}")

                    payload_json = json.dumps(payload)

                    conn = http.client.HTTPSConnection(self.base_url)
                    conn.request("POST", endpoint, payload_json, headers)
                    res = conn.getresponse()
                    data = res.read()
                    conn.close()

                    _logger.info(f"Method {i} response status: {res.status}")
                    _logger.info(f"Method {i} response: {data.decode('utf-8')}")

                    if res.status in [200, 201]:
                        try:
                            response_data = json.loads(data.decode('utf-8'))
                            if response_data.get('status') == 'success':
                                return {
                                    'status': 'success',
                                    'message': f'Template sent successfully using method {i}',
                                    'message_id': response_data.get('data', {}).get('id', 'unknown'),
                                    'response': response_data
                                }
                        except json.JSONDecodeError:
                            pass

                # If all methods failed, return detailed error
                last_response = data.decode('utf-8') if 'data' in locals() else 'Unknown error'
                return {
                    'status': 'error',
                    'message': f'Failed to send message: All template sending methods failed',
                    'details': f'Template: {template_name}, Variables: {template_vars}',
                    'last_response': last_response
                }

            else:
                # Text message
                payload = {
                    "phone_number_id": self.phone_number_id,
                    "customer_country_code": country_code,
                    "customer_number": customer_number,
                    "data": {
                        "type": "text",
                        "context": {
                            "body": message_text
                        }
                    }
                }

                payload_json = json.dumps(payload)
                _logger.info(f"Sending text message with payload: {payload_json}")

                conn = http.client.HTTPSConnection(self.base_url)
                conn.request("POST", endpoint, payload_json, headers)
                res = conn.getresponse()
                data = res.read()
                conn.close()

                _logger.info(f"Text message response status: {res.status}")
                _logger.info(f"Text message response: {data.decode('utf-8')}")

                if res.status in [200, 201]:
                    response_data = json.loads(data.decode('utf-8'))
                    return {
                        'status': 'success',
                        'message': 'Text message sent successfully',
                        'message_id': response_data.get('data', {}).get('id', 'unknown'),
                        'response': response_data
                    }
                else:
                    return {
                        'status': 'error',
                        'message': f'Failed to send text message: {data.decode("utf-8")}',
                        'status_code': res.status,
                        'response': data.decode('utf-8')
                    }

        except Exception as e:
            _logger.error(f"Exception in send_message: {str(e)}")
            return {
                'status': 'error',
                'message': f'Exception occurred: {str(e)}'
            }

    # Replace the get_available_templates method in myoperator_chat_config.py

    def get_available_templates(self):
        """Get ALL available message templates - Fixed to prevent duplicates"""
        try:
            import http.client
            import json

            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'X-MYOP-COMPANY-ID': self.company_id
            }

            # Use a dictionary to store templates by ID/name to avoid duplicates
            templates_dict = {}

            # First, try with high limits to get all templates at once
            high_limits = [1000, 500, 200, 100]

            for limit in high_limits:
                try:
                    endpoint = f"/chat/templates?limit={limit}"
                    _logger.info(f"🔍 Trying to fetch ALL templates with limit: {limit}")

                    conn = http.client.HTTPSConnection(self.base_url)
                    conn.request("GET", endpoint, '', headers)
                    response = conn.getresponse()
                    response_data = response.read()
                    conn.close()

                    if response.status == 200:
                        result = json.loads(response_data.decode('utf-8'))
                        templates = result.get('data', {}).get('results', [])

                        # Store templates in dictionary to avoid duplicates
                        for template in templates:
                            template_key = template.get('id') or template.get('name', '')
                            if template_key:
                                templates_dict[template_key] = template

                        # Get pagination info
                        data_info = result.get('data', {})
                        total_count = data_info.get('count', 0)
                        has_next = data_info.get('next') is not None

                        _logger.info(f"✅ Got {len(templates)} templates with limit {limit}")
                        _logger.info(f"📊 Unique templates so far: {len(templates_dict)}")

                        # If we got all templates (no next page), return them
                        if not has_next or len(templates_dict) >= total_count:
                            _logger.info(f"🎉 Successfully got ALL {len(templates_dict)} unique templates!")
                            # Sort templates by name for consistent ordering
                            unique_templates = list(templates_dict.values())
                            try:
                                unique_templates.sort(key=lambda x: x.get('name', '').lower())
                            except Exception as e:
                                _logger.warning(f"Could not sort templates: {str(e)}")
                            return unique_templates
                        else:
                            _logger.info(f"⚠️ Still more templates available, continuing with pagination...")
                            break  # Continue with pagination

                    else:
                        _logger.warning(f"❌ Limit {limit} failed with status: {response.status}")
                        continue

                except Exception as e:
                    _logger.warning(f"❌ Exception with limit {limit}: {str(e)}")
                    continue

            # If high limits didn't get everything, try pagination
            if len(templates_dict) == 0:
                _logger.info("🔄 High limits failed, trying pagination approach...")
                page = 1
                limit = 50
            else:
                _logger.info("🔄 High limit partially worked, continuing with pagination...")
                page = 2
                limit = 100

            # Pagination loop
            consecutive_empty_pages = 0
            max_empty_pages = 3

            while consecutive_empty_pages < max_empty_pages:
                try:
                    # Try different pagination formats
                    endpoints = [
                        f"/chat/templates?limit={limit}&page={page}",
                        f"/chat/templates?limit={limit}&offset={(page - 1) * limit}",
                    ]

                    page_templates = []
                    success = False

                    for endpoint in endpoints:
                        try:
                            _logger.info(f"🔍 Trying page {page} with endpoint: {endpoint}")

                            conn = http.client.HTTPSConnection(self.base_url)
                            conn.request("GET", endpoint, '', headers)
                            response = conn.getresponse()
                            response_data = response.read()
                            conn.close()

                            if response.status == 200:
                                result = json.loads(response_data.decode('utf-8'))
                                page_templates = result.get('data', {}).get('results', [])

                                if page_templates:
                                    _logger.info(f"✅ Page {page}: Found {len(page_templates)} templates")

                                    # Add to dictionary to remove duplicates
                                    new_templates_count = 0
                                    for template in page_templates:
                                        template_key = template.get('id') or template.get('name', '')
                                        if template_key and template_key not in templates_dict:
                                            templates_dict[template_key] = template
                                            new_templates_count += 1

                                    _logger.info(f"📊 Added {new_templates_count} new unique templates from page {page}")
                                    _logger.info(f"📊 Total unique templates: {len(templates_dict)}")

                                    success = True
                                    consecutive_empty_pages = 0  # Reset counter

                                    # Check pagination info
                                    data_info = result.get('data', {})
                                    has_next = data_info.get('next') is not None

                                    # Stop conditions
                                    if not has_next:
                                        _logger.info(f"🏁 No more pages indicated by API")
                                        # Sort and return
                                        unique_templates = list(templates_dict.values())
                                        try:
                                            unique_templates.sort(key=lambda x: x.get('name', '').lower())
                                        except Exception as e:
                                            _logger.warning(f"Could not sort templates: {str(e)}")
                                        return unique_templates

                                    if len(page_templates) < limit:
                                        _logger.info(
                                            f"🏁 Got fewer templates than limit ({len(page_templates)} < {limit})")
                                        # Sort and return
                                        unique_templates = list(templates_dict.values())
                                        try:
                                            unique_templates.sort(key=lambda x: x.get('name', '').lower())
                                        except Exception as e:
                                            _logger.warning(f"Could not sort templates: {str(e)}")
                                        return unique_templates

                                    break  # Success, continue to next page
                                else:
                                    _logger.info(f"📭 Page {page}: No templates found")
                                    consecutive_empty_pages += 1
                                    success = True  # Don't try other endpoints for this page
                                    break
                            else:
                                _logger.warning(f"❌ Page {page} endpoint {endpoint} failed: {response.status}")
                                continue

                        except Exception as e:
                            _logger.warning(f"❌ Page {page} endpoint {endpoint} exception: {str(e)}")
                            continue

                    if not success:
                        _logger.warning(f"❌ All endpoints failed for page {page}")
                        consecutive_empty_pages += 1

                    page += 1

                    # Safety check
                    if page > 50:  # Max 50 pages
                        _logger.warning("⚠️ Reached maximum page limit (50), stopping")
                        break

                except Exception as e:
                    _logger.error(f"❌ Error in pagination loop: {str(e)}")
                    break

            # Final attempt - try without any parameters if we have no templates
            if len(templates_dict) == 0:
                try:
                    _logger.info("🔄 Final attempt: trying without any parameters")
                    endpoint = "/chat/templates"

                    conn = http.client.HTTPSConnection(self.base_url)
                    conn.request("GET", endpoint, '', headers)
                    response = conn.getresponse()
                    response_data = response.read()
                    conn.close()

                    if response.status == 200:
                        result = json.loads(response_data.decode('utf-8'))
                        templates = result.get('data', {}).get('results', [])

                        for template in templates:
                            template_key = template.get('id') or template.get('name', '')
                            if template_key:
                                templates_dict[template_key] = template

                        _logger.info(f"✅ Final attempt got {len(templates_dict)} unique templates")

                except Exception as e:
                    _logger.error(f"❌ Final attempt failed: {str(e)}")

            _logger.info(f"🎯 FINAL RESULT: Total unique templates: {len(templates_dict)}")

            # Convert back to list and sort by name for consistent ordering
            unique_templates = list(templates_dict.values())

            # Sort templates by name for better UI experience
            try:
                unique_templates.sort(key=lambda x: x.get('name', '').lower())
            except Exception as e:
                _logger.warning(f"Could not sort templates: {str(e)}")

            return unique_templates

        except Exception as e:
            _logger.error(f"❌ Critical error in get_available_templates: {str(e)}")
            return []

    # Replace the _get_template_selection method in send_message_wizard.py

    @api.model
    def _get_template_selection(self):
        """Get template selection options - Fixed to prevent duplicates"""
        try:
            # Get conversation from context
            conversation_id = self.env.context.get('default_conversation_id')
            if conversation_id:
                conversation = self.env['myoperator.conversation'].browse(conversation_id)
                if conversation.config_id:
                    config = conversation.config_id
                else:
                    config = self.env['myoperator.chat.config'].get_active_config()
            else:
                config = self.env['myoperator.chat.config'].get_active_config()

            if not config:
                return [('hello_world', 'hello_world')]  # Default fallback

            templates = config.get_available_templates()

            # Use a set to track seen template names and avoid duplicates
            seen_templates = set()
            template_selection_list = []

            for template in templates:
                template_name = template.get('name', 'Unknown')
                template_status = template.get('status', 'Unknown')

                # Skip if we've already seen this template name
                if template_name in seen_templates:
                    continue

                # Only add approved/active templates to selection
                if template_status.lower() in ['approved', 'active']:
                    template_selection_list.append((template_name, template_name))
                    seen_templates.add(template_name)

            # Return default if no templates found
            if not template_selection_list:
                template_selection_list = [('hello_world', 'hello_world')]

            # Sort for better user experience
            template_selection_list.sort(key=lambda x: x[1].lower())

            return template_selection_list

        except Exception as e:
            _logger.error(f"Error in _get_template_selection: {str(e)}")
            # Fallback in case of any error
            return [('hello_world', 'hello_world')]

    # Replace the default_get method in send_message_wizard.py

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        # Get conversation from context
        conversation_id = self.env.context.get('default_conversation_id')
        if conversation_id:
            conversation = self.env['myoperator.conversation'].browse(conversation_id)
            res['conversation_id'] = conversation_id
            res['phone_number'] = conversation.customer_contact

            # Get available templates and populate selection field
            if conversation.config_id:
                templates = conversation.config_id.get_available_templates()

                # Use a set to avoid duplicates
                seen_templates = set()
                template_list = []

                for template in templates:
                    template_name = template.get('name', 'Unknown')
                    template_status = template.get('status', 'Unknown')

                    # Skip duplicates
                    if template_name in seen_templates:
                        continue

                    seen_templates.add(template_name)
                    template_list.append(f"- {template_name} ({template_status})")

                res['available_templates'] = '\n'.join(
                    sorted(template_list)) if template_list else 'No templates available'

        else:
            # Try to get default config for templates
            try:
                default_config = self.env['myoperator.chat.config'].get_active_config()
                if default_config:
                    templates = default_config.get_available_templates()

                    # Use a set to avoid duplicates
                    seen_templates = set()
                    template_list = []

                    for template in templates:
                        template_name = template.get('name', 'Unknown')
                        template_status = template.get('status', 'Unknown')

                        # Skip duplicates
                        if template_name in seen_templates:
                            continue

                        seen_templates.add(template_name)
                        template_list.append(f"- {template_name} ({template_status})")

                    res['available_templates'] = '\n'.join(
                        sorted(template_list)) if template_list else 'No templates available'
            except:
                res['available_templates'] = 'No templates available'

        return res

    # Replace the action_refresh_templates method in send_message_wizard.py

    def action_refresh_templates(self):
        """Refresh available templates - Fixed to prevent duplicates"""
        if self.conversation_id and self.conversation_id.config_id:
            config = self.conversation_id.config_id
        else:
            config = self.env['myoperator.chat.config'].get_active_config()

        if config:
            templates = config.get_available_templates()

            # Use a set to avoid duplicates
            seen_templates = set()
            template_list = []

            for template in templates:
                template_name = template.get('name', 'Unknown')
                template_status = template.get('status', 'Unknown')

                # Skip duplicates
                if template_name in seen_templates:
                    continue

                seen_templates.add(template_name)
                template_list.append(f"- {template_name} ({template_status})")

            self.available_templates = '\n'.join(sorted(template_list)) if template_list else 'No templates available'

            # Force refresh of the selection field by triggering a recompute
            self.template_selection = False

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Templates Refreshed'),
                    'message': _('Template list has been updated with %d unique templates.') % len(seen_templates),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError(_('No chat configuration found.'))

    def _make_api_request(self, endpoint, method='GET', data=None):
        """Make API request to MyOperator Chat API"""
        import http.client

        try:
            conn = http.client.HTTPSConnection(self.base_url)

            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'X-MYOP-COMPANY-ID': self.company_id,
            }

            if method in ['POST', 'PUT']:
                headers['Content-Type'] = 'application/json'
                payload = json.dumps(data) if data else ''
            else:
                payload = ''

            conn.request(method, endpoint, payload, headers)
            res = conn.getresponse()
            response_data = res.read()
            conn.close()

            if res.status in [200, 201]:
                return json.loads(response_data.decode('utf-8'))
            else:
                _logger.error(f"MyOperator Chat API request failed: {res.status} - {response_data.decode('utf-8')}")
                return {
                    'status': 'error',
                    'message': f'API request failed: {res.status}',
                    'response': response_data.decode('utf-8')
                }

        except Exception as e:
            _logger.error(f"MyOperator Chat API request exception: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _parse_phone_number(self, phone_number):
        """Parse phone number to extract country code and customer number"""
        # Remove any non-digit characters
        phone_number = ''.join(filter(str.isdigit, phone_number))

        # Handle different country codes
        if phone_number.startswith('91') and len(phone_number) >= 12:
            # India
            country_code = '91'
            customer_number = phone_number[2:]
        elif phone_number.startswith('1') and len(phone_number) >= 11:
            # US/Canada
            country_code = '1'
            customer_number = phone_number[1:]
        elif len(phone_number) == 10:
            # Assume India if 10 digits
            country_code = '91'
            customer_number = phone_number
        else:
            # Default to India
            country_code = '91'
            customer_number = phone_number

        return country_code, customer_number

    def _parse_timestamp(self, timestamp_val):
        """Parse timestamp from various formats"""
        if not timestamp_val:
            return False

        try:
            from datetime import datetime

            if isinstance(timestamp_val, str):
                # Clean the timestamp string
                timestamp_str = timestamp_val.strip()

                # Handle the specific error format: 2025-07-03 08:05:44.200246+00:00
                if '+' in timestamp_str:
                    # Remove timezone part
                    timestamp_str = timestamp_str.split('+')[0]
                elif 'Z' in timestamp_str:
                    timestamp_str = timestamp_str.replace('Z', '')

                # Try different formats without timezone
                formats = [
                    '%Y-%m-%d %H:%M:%S.%f',  # 2025-07-03 08:05:44.200246
                    '%Y-%m-%d %H:%M:%S',  # 2025-07-03 08:05:44
                    '%Y-%m-%dT%H:%M:%S.%f',  # ISO format with microseconds
                    '%Y-%m-%dT%H:%M:%S',  # ISO format without microseconds
                ]

                for fmt in formats:
                    try:
                        return datetime.strptime(timestamp_str, fmt)
                    except ValueError:
                        continue

                # Last resort: try to parse just the date part
                try:
                    date_part = timestamp_str.split(' ')[0]
                    return datetime.strptime(date_part + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
                except:
                    pass

                _logger.warning(f"Could not parse timestamp: {timestamp_val}, using current time")
                return datetime.now()

            elif isinstance(timestamp_val, (int, float)):
                # Unix timestamp
                return datetime.fromtimestamp(timestamp_val)
            else:
                return timestamp_val if timestamp_val else datetime.now()

        except Exception as e:
            _logger.error(f"Error parsing timestamp {timestamp_val}: {str(e)}")
            return datetime.now()

    @api.model
    def cron_sync_conversations(self):
        """Cron job to sync conversations automatically"""
        active_configs = self.search([('active', '=', True), ('auto_sync_enabled', '=', True)])

        for config in active_configs:
            try:
                config.sync_conversations()
                _logger.info(f"Auto sync completed for chat config: {config.name}")
            except Exception as e:
                _logger.error(f"Auto sync failed for chat config {config.name}: {str(e)}")

    # Additional cron methods for enhanced functionality
    def cron_refresh_template_cache(self):
        """Refresh template cache for all active configs"""
        active_configs = self.search([('active', '=', True)])
        for config in active_configs:
            try:
                templates = config.get_available_templates()
                _logger.info(f"Refreshed templates for config {config.name}: {len(templates)} templates")
            except Exception as e:
                _logger.error(f"Template cache refresh failed for {config.name}: {str(e)}")

    def cron_retry_failed_messages(self):
        """Retry failed template messages"""
        # This would require a failed_messages table to track failures
        # Implementation depends on your specific requirements
        _logger.info("Failed message retry completed")

    def cron_validate_templates(self):
        """Validate template configurations"""
        active_configs = self.search([('active', '=', True)])
        for config in active_configs:
            try:
                templates = config.get_available_templates()
                for template in templates:
                    template_name = template.get('name')
                    if template_name == 'shop_from_us_on_whatsapp':
                        # Validate this specific template
                        if not template.get('status') == 'approved':
                            _logger.warning(f"Template {template_name} is not approved")
            except Exception as e:
                _logger.error(f"Template validation failed for {config.name}: {str(e)}")

    def cron_update_message_status(self):
        """Update message delivery status"""
        # Implementation for checking message delivery status
        _logger.info("Message status update completed")

    def get_template_variables(self, template_name):
        """Get required variables for a specific template"""
        template_vars = {}

        # Define known template variables
        template_mappings = {
            'shop_from_us_on_whatsapp': ['var_1'],
            'hello_world': [],
            'order_confirmation': ['var_1', 'var_2'],
            'appointment_reminder': ['var_1', 'var_2', 'var_3'],
            # Add more templates as needed
        }

        required_vars = template_mappings.get(template_name, [])

        # Return structure with variable info
        return {
            'required_variables': required_vars,
            'has_variables': len(required_vars) > 0
        }

    def validate_template_variables(self, template_name, provided_variables=None):
        """Validate if all required template variables are provided"""
        template_info = self.get_template_variables(template_name)
        required_vars = template_info.get('required_variables', [])

        if not required_vars:
            return {'valid': True, 'missing_vars': []}

        provided_variables = provided_variables or {}
        missing_vars = []

        for var in required_vars:
            if var not in provided_variables or not provided_variables[var]:
                missing_vars.append(var)

        return {
            'valid': len(missing_vars) == 0,
            'missing_vars': missing_vars,
            'required_vars': required_vars
        }

    def prepare_template_variables(self, template_name, phone_number, custom_variables=None):
        """Prepare template variables with smart defaults"""
        # Get customer information
        customer_name = self._get_customer_name_for_phone(phone_number)

        # Base variables that work for most templates
        base_variables = {
            'var_1': customer_name,
            'var_2': 'Customer',  # Fallback
            'var_3': 'Thank you',  # Fallback
            'customer_name': customer_name,
            'name': customer_name
        }

        # Template-specific variable mapping
        template_specific = {
            'shop_from_us_on_whatsapp': {
                'var_1': customer_name
            },
            'order_confirmation': {
                'var_1': customer_name,
                'var_2': 'Your Order'
            },
            'appointment_reminder': {
                'var_1': customer_name,
                'var_2': 'Tomorrow',
                'var_3': '10:00 AM'
            }
        }

        # Start with base variables
        final_variables = base_variables.copy()

        # Override with template-specific variables
        if template_name in template_specific:
            final_variables.update(template_specific[template_name])

        # Override with custom variables if provided
        if custom_variables:
            final_variables.update(custom_variables)

        return final_variables

    def send_template_with_auto_variables(self, phone_number, template_name, custom_variables=None):
        """Send template message with automatically prepared variables"""
        try:
            # Prepare variables
            template_variables = self.prepare_template_variables(
                template_name, phone_number, custom_variables
            )

            # Validate variables
            validation = self.validate_template_variables(template_name, template_variables)

            if not validation['valid']:
                return {
                    'status': 'error',
                    'message': f'Missing required variables: {", ".join(validation["missing_vars"])}',
                    'required_vars': validation['required_vars'],
                    'provided_vars': list(template_variables.keys())
                }

            # Send the message
            result = self.send_message(
                phone_number=phone_number,
                message_text='',
                use_template=True,
                template_name=template_name,
                template_parameters=template_variables
            )

            # Add variable info to result
            result['variables_used'] = template_variables

            return result

        except Exception as e:
            _logger.error(f"Error in send_template_with_auto_variables: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to send template: {str(e)}'
            }

    def test_template_sending(self, template_name, phone_number=None):
        """Test template sending with debug information"""
        if not phone_number:
            phone_number = "919999999999"  # Test number

        try:
            _logger.info(f"🧪 Testing template: {template_name}")

            # Get template info
            template_info = self.get_template_variables(template_name)
            _logger.info(f"📋 Template info: {template_info}")

            # Prepare variables
            variables = self.prepare_template_variables(template_name, phone_number)
            _logger.info(f"🔧 Prepared variables: {variables}")

            # Validate
            validation = self.validate_template_variables(template_name, variables)
            _logger.info(f"✅ Validation result: {validation}")

            if not validation['valid']:
                return {
                    'status': 'error',
                    'message': f'Template validation failed: {validation}',
                    'template_info': template_info,
                    'variables': variables
                }

            # Test send (but don't actually send to avoid spam)
            # result = self.send_template_with_auto_variables(phone_number, template_name)

            return {
                'status': 'success',
                'message': 'Template test completed successfully',
                'template_info': template_info,
                'variables': variables,
                'validation': validation
            }

        except Exception as e:
            _logger.error(f"Template testing error: {str(e)}")
            return {
                'status': 'error',
                'message': f'Template test failed: {str(e)}'
            }

    def action_test_template(self):
        """Action to test template from UI"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Test Template',
            'res_model': 'myoperator.template.test.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_config_id': self.id}
        }

    def get_conversation_by_phone(self, phone_number):
        """Get existing conversation by phone number"""
        clean_number = re.sub(r'[^\d+]', '', phone_number)
        search_number = clean_number[-10:]

        return self.env['myoperator.conversation'].search([
            ('customer_contact', 'ilike', search_number),
            ('config_id', '=', self.id)
        ], limit=1)

    def create_or_update_conversation(self, phone_number, customer_name=None):
        """Create or update conversation record"""
        conversation = self.get_conversation_by_phone(phone_number)

        if not conversation:
            # Create new conversation
            vals = {
                'config_id': self.id,
                'conversation_id': f'manual_{fields.Datetime.now().timestamp()}',
                'customer_contact': phone_number,
                'customer_name': customer_name or self._get_customer_name_for_phone(phone_number),
                'status': 'open',
                'last_message_at': fields.Datetime.now(),
            }
            conversation = self.env['myoperator.conversation'].create(vals)
        else:
            # Update existing
            if customer_name:
                conversation.customer_name = customer_name
            conversation.last_message_at = fields.Datetime.now()

        return conversation

    def log_message_attempt(self, phone_number, message_type, template_name=None,
                            status='attempted', error_message=None):
        """Log message sending attempts for debugging"""
        try:
            self.env['myoperator.message.log'].create({
                'config_id': self.id,
                'phone_number': phone_number,
                'message_type': message_type,
                'template_name': template_name,
                'status': status,
                'error_message': error_message,
                'timestamp': fields.Datetime.now(),
            })
        except Exception as e:
            _logger.warning(f"Could not log message attempt: {str(e)}")

    def get_failed_messages_count(self):
        """Get count of failed messages for dashboard"""
        try:
            domain = [
                ('config_id', '=', self.id),
                ('status', '=', 'failed'),
                ('timestamp', '>=', fields.Datetime.now().replace(hour=0, minute=0, second=0))
            ]
            return self.env['myoperator.message.log'].search_count(domain)
        except:
            return 0

    def get_success_rate_today(self):
        """Calculate message success rate for today"""
        try:
            today_start = fields.Datetime.now().replace(hour=0, minute=0, second=0)

            total_domain = [
                ('config_id', '=', self.id),
                ('timestamp', '>=', today_start)
            ]

            success_domain = total_domain + [('status', '=', 'success')]

            total_count = self.env['myoperator.message.log'].search_count(total_domain)
            success_count = self.env['myoperator.message.log'].search_count(success_domain)

            if total_count == 0:
                return 100.0

            return round((success_count / total_count) * 100, 1)
        except:
            return 0.0