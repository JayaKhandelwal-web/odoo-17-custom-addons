import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MyOperatorChatWebhook(http.Controller):

    @http.route('/myoperator/chat/webhook', type='json', auth='none', methods=['POST'], csrf=False)
    def chat_webhook_handler(self):
        """Handle chat webhooks from MyOperator"""
        try:
            data = request.jsonrequest
            _logger.info(f"MyOperator chat webhook received: {data}")

            # Process different webhook events
            event_type = data.get('event_type') or data.get('type')

            if event_type == 'message_received':
                self._handle_message_received(data)
            elif event_type == 'message_sent':
                self._handle_message_sent(data)
            elif event_type == 'conversation_assigned':
                self._handle_conversation_assigned(data)
            elif event_type == 'conversation_resolved':
                self._handle_conversation_resolved(data)

            return {'status': 'success'}

        except Exception as e:
            _logger.error(f"MyOperator chat webhook error: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _handle_message_received(self, data):
        """Handle incoming message webhook"""
        try:
            message_data = data.get('message', {})
            conversation_data = data.get('conversation', {})

            # Find or create conversation
            MyOperatorConversation = request.env['myoperator.conversation'].sudo()
            MyOperatorMessage = request.env['myoperator.message'].sudo()

            conversation = MyOperatorConversation.search([
                ('conversation_id', '=', conversation_data.get('id'))
            ], limit=1)

            if not conversation:
                # Create conversation if it doesn't exist
                config = self._get_active_chat_config()
                if config:
                    conversation_vals = {
                        'config_id': config.id,
                        'conversation_id': conversation_data.get('id'),
                        'customer_name': conversation_data.get('customer_name'),
                        'customer_contact': conversation_data.get('customer_contact'),
                        'status': conversation_data.get('status', 'open'),
                        'last_message_at': self._parse_timestamp(message_data.get('timestamp')),
                    }
                    conversation = MyOperatorConversation.create(conversation_vals)

            if conversation:
                # Create message record
                message_vals = {
                    'conversation_id': conversation.id,
                    'message_id': message_data.get('id'),
                    'direction': 'incoming',
                    'message_type': self._get_message_type(message_data),
                    'content': self._extract_message_content(message_data),
                    'timestamp': self._parse_timestamp(message_data.get('timestamp')),
                    'media_url': self._extract_media_url(message_data),
                    'media_filename': self._extract_media_filename(message_data),
                }

                # Check if message already exists
                existing_message = MyOperatorMessage.search([
                    ('message_id', '=', message_data.get('id'))
                ], limit=1)

                if not existing_message:
                    MyOperatorMessage.create(message_vals)

                    # Update conversation
                    conversation.write({
                        'last_message_at': message_vals['timestamp'],
                        'unread_count': conversation.unread_count + 1,
                        'status': 'open'
                    })

                    # Send auto-reply if enabled
                    if conversation.config_id.auto_reply_enabled and conversation.config_id.auto_reply_message:
                        self._send_auto_reply(conversation)

        except Exception as e:
            _logger.error(f"Error handling message received webhook: {str(e)}")

    def _handle_message_sent(self, data):
        """Handle outgoing message webhook"""
        try:
            message_data = data.get('message', {})
            conversation_data = data.get('conversation', {})

            MyOperatorConversation = request.env['myoperator.conversation'].sudo()
            MyOperatorMessage = request.env['myoperator.message'].sudo()

            conversation = MyOperatorConversation.search([
                ('conversation_id', '=', conversation_data.get('id'))
            ], limit=1)

            if conversation:
                # Create or update message record
                message_vals = {
                    'conversation_id': conversation.id,
                    'message_id': message_data.get('id'),
                    'direction': 'outgoing',
                    'message_type': self._get_message_type(message_data),
                    'content': self._extract_message_content(message_data),
                    'timestamp': self._parse_timestamp(message_data.get('timestamp')),
                    'delivered_status': True,
                }

                existing_message = MyOperatorMessage.search([
                    ('message_id', '=', message_data.get('id'))
                ], limit=1)

                if existing_message:
                    existing_message.write(message_vals)
                else:
                    MyOperatorMessage.create(message_vals)

                # Update conversation
                conversation.write({
                    'last_message_at': message_vals['timestamp'],
                })

        except Exception as e:
            _logger.error(f"Error handling message sent webhook: {str(e)}")

    def _handle_conversation_assigned(self, data):
        """Handle conversation assignment webhook"""
        try:
            conversation_data = data.get('conversation', {})
            agent_data = data.get('agent', {})

            MyOperatorConversation = request.env['myoperator.conversation'].sudo()

            conversation = MyOperatorConversation.search([
                ('conversation_id', '=', conversation_data.get('id'))
            ], limit=1)

            if conversation:
                # Find Odoo user by email
                agent_email = agent_data.get('email')
                odoo_user = None
                if agent_email:
                    odoo_user = request.env['res.users'].sudo().search([
                        ('email', '=', agent_email)
                    ], limit=1)

                conversation.write({
                    'status': 'assigned',
                    'assigned_user_id': odoo_user.id if odoo_user else False,
                })

        except Exception as e:
            _logger.error(f"Error handling conversation assigned webhook: {str(e)}")

    def _handle_conversation_resolved(self, data):
        """Handle conversation resolved webhook"""
        try:
            conversation_data = data.get('conversation', {})

            MyOperatorConversation = request.env['myoperator.conversation'].sudo()

            conversation = MyOperatorConversation.search([
                ('conversation_id', '=', conversation_data.get('id'))
            ], limit=1)

            if conversation:
                conversation.write({
                    'status': 'resolved',
                    'unread_count': 0,
                })

        except Exception as e:
            _logger.error(f"Error handling conversation resolved webhook: {str(e)}")

    def _get_active_chat_config(self):
        """Get active chat configuration"""
        try:
            return request.env['myoperator.chat.config'].sudo().search([
                ('active', '=', True)
            ], limit=1)
        except:
            return None

    def _parse_timestamp(self, timestamp_val):
        """Parse timestamp from webhook data"""
        if not timestamp_val:
            return False
        try:
            from datetime import datetime
            if isinstance(timestamp_val, str):
                # Handle different timestamp formats
                timestamp_str = timestamp_val.replace('Z', '+00:00')

                # Try different formats
                formats = [
                    '%Y-%m-%d %H:%M:%S.%f%z',  # 2025-07-03 08:05:44.200246+00:00
                    '%Y-%m-%d %H:%M:%S%z',  # 2025-07-03 08:05:44+00:00
                    '%Y-%m-%dT%H:%M:%S.%f%z',  # ISO format with microseconds
                    '%Y-%m-%dT%H:%M:%S%z',  # ISO format without microseconds
                    '%Y-%m-%d %H:%M:%S.%f',  # Without timezone
                    '%Y-%m-%d %H:%M:%S',  # Simple format
                ]

                for fmt in formats:
                    try:
                        parsed_dt = datetime.strptime(timestamp_str, fmt)
                        # Convert to naive datetime for Odoo
                        if parsed_dt.tzinfo:
                            parsed_dt = parsed_dt.replace(tzinfo=None)
                        return parsed_dt
                    except ValueError:
                        continue

                # If all formats fail, try fromisoformat
                try:
                    parsed_dt = datetime.fromisoformat(timestamp_str)
                    if parsed_dt.tzinfo:
                        parsed_dt = parsed_dt.replace(tzinfo=None)
                    return parsed_dt
                except ValueError:
                    pass

                # Return current time as fallback
                return datetime.now()

            elif isinstance(timestamp_val, (int, float)):
                return datetime.fromtimestamp(timestamp_val)
            else:
                return timestamp_val
        except Exception as e:
            _logger.error(f"Error parsing timestamp {timestamp_val}: {str(e)}")
            return datetime.now()

    def _get_message_type(self, message_data):
        """Extract message type from webhook data"""
        data = message_data.get('data', {})
        return data.get('type', 'text')

    def _extract_message_content(self, message_data):
        """Extract message content from webhook data"""
        data = message_data.get('data', {})

        # For text messages
        if isinstance(data, dict):
            context = data.get('context', {})
            if isinstance(context, dict):
                body = context.get('body', '')
                if body:
                    return body

        # Fallback methods
        for field in ['body', 'message', 'text', 'content']:
            value = message_data.get(field, '')
            if value:
                return value

        return 'No content'

    def _extract_media_url(self, message_data):
        """Extract media URL from webhook data"""
        data = message_data.get('data', {})
        if isinstance(data, dict):
            context = data.get('context', {})
            if isinstance(context, dict):
                return context.get('url', context.get('media_url', ''))
        return ''

    def _extract_media_filename(self, message_data):
        """Extract media filename from webhook data"""
        data = message_data.get('data', {})
        if isinstance(data, dict):
            context = data.get('context', {})
            if isinstance(context, dict):
                return context.get('filename', context.get('name', ''))
        return ''

    def _send_auto_reply(self, conversation):
        """Send automatic reply to incoming message"""
        try:
            if conversation.config_id.auto_reply_enabled and conversation.config_id.auto_reply_message:
                result = conversation.config_id.send_message(
                    conversation.customer_contact,
                    conversation.config_id.auto_reply_message
                )

                if result.get('status') == 'success':
                    # Create message record for auto-reply
                    request.env['myoperator.message'].sudo().create({
                        'conversation_id': conversation.id,
                        'message_id': f"auto_reply_{result.get('message_id', 'temp')}",
                        'direction': 'outgoing',
                        'message_type': 'text',
                        'content': conversation.config_id.auto_reply_message,
                        'timestamp': request.env['myoperator.message']._fields['timestamp'].default(),
                    })

                    _logger.info(f"Auto-reply sent for conversation {conversation.conversation_id}")

        except Exception as e:
            _logger.error(f"Error sending auto-reply: {str(e)}")