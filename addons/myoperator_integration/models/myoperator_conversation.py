from odoo import models, fields, api, _
from datetime import datetime
import logging
import uuid

_logger = logging.getLogger(__name__)


class MyOperatorConversation(models.Model):
    _name = 'myoperator.conversation'
    _description = 'MyOperator Conversation'
    _order = 'last_message_at desc'
    _rec_name = 'display_name'

    config_id = fields.Many2one('myoperator.chat.config', string='Chat Configuration', required=True)
    conversation_id = fields.Char('Conversation ID', required=True, index=True)
    customer_name = fields.Char('Customer Name', index=True)
    customer_contact = fields.Char('Customer Contact', index=True)

    status = fields.Selection([
        ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('closed', 'Closed'),
        ('resolved', 'Resolved'),
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ], string='Status', default='open')

    unread_count = fields.Integer('Unread Messages', default=0)
    message_count = fields.Integer('Message Count', compute='_compute_message_count')
    last_message_at = fields.Datetime('Last Message')

    # Related partner information
    partner_id = fields.Many2one('res.partner', string='Related Contact',
                                 compute='_compute_partner', store=True)

    # Message relationship
    message_ids = fields.One2many('myoperator.message', 'conversation_id', string='Messages')

    # Additional fields
    notes = fields.Text('Notes')
    assigned_user_id = fields.Many2one('res.users', string='Assigned Agent')
    synced_date = fields.Datetime('Synced Date', default=fields.Datetime.now)
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('unique_conversation_id_config', 'unique(conversation_id, config_id)',
         'Conversation ID must be unique per configuration!')
    ]

    @api.depends('customer_contact')
    def _compute_partner(self):
        for record in self:
            if record.customer_contact:
                # Clean phone number for search
                clean_number = ''.join(filter(str.isdigit, record.customer_contact))[-10:]
                partner = self.env['res.partner'].search([
                    '|', ('phone', 'ilike', clean_number),
                    ('mobile', 'ilike', clean_number)
                ], limit=1)
                record.partner_id = partner.id if partner else False
            else:
                record.partner_id = False

    @api.depends('message_ids')
    def _compute_message_count(self):
        for record in self:
            record.message_count = len(record.message_ids)

    @api.depends('customer_name', 'customer_contact', 'last_message_at')
    def _compute_display_name(self):
        for record in self:
            name = record.customer_name or record.customer_contact or 'Unknown'
            if record.last_message_at:
                name += f" ({record.last_message_at.strftime('%Y-%m-%d %H:%M')})"
            record.display_name = name

    def action_open_chat_interface(self):
        """Open WhatsApp-like chat interface"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Chat - {self.customer_name or self.customer_contact}',
            'res_model': 'myoperator.conversation',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('myoperator_integration.view_myoperator_conversation_chat_form').id,
            'target': 'current',
        }

    def action_sync_messages(self):
        """Sync messages for this conversation"""
        try:
            result = self.config_id._make_api_request(f'/chat/conversations/{self.conversation_id}/messages?limit=100')

            if 'data' in result and 'results' in result['data']:
                messages = result['data']['results']
                MyOperatorMessage = self.env['myoperator.message']

                synced_count = 0
                for msg_data in messages:
                    api_message_id = msg_data.get('id')
                    if not api_message_id:
                        continue

                    # Check if message already exists
                    existing_msg = MyOperatorMessage.search([
                        ('message_id', '=', api_message_id)
                    ], limit=1)

                    if not existing_msg:
                        try:
                            vals = {
                                'conversation_id': self.id,
                                'message_id': api_message_id,
                                'direction': self._map_message_direction(msg_data),
                                'message_type': self._get_message_type(msg_data),
                                'content': self._extract_message_content(msg_data),
                                'timestamp': self.config_id._parse_timestamp(
                                    msg_data.get('created') or msg_data.get('timestamp')
                                ),
                            }
                            MyOperatorMessage.create(vals)
                            synced_count += 1
                        except Exception as e:
                            _logger.warning(f"Failed to create message {api_message_id}: {str(e)}")
                            continue

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Sync Complete'),
                        'message': _('Synced %d new messages') % synced_count,
                        'type': 'success',
                    }
                }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sync Failed'),
                    'message': str(e),
                    'type': 'danger',
                }
            }

    def action_send_message(self):
        """Open send message wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Message'),
            'res_model': 'myoperator.send.message.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_conversation_id': self.id,
                'default_phone_number': self.customer_contact,
            }
        }

    def action_assign_to_me(self):
        """Assign conversation to current user"""
        self.assigned_user_id = self.env.user
        self.status = 'assigned'

    def action_mark_resolved(self):
        """Mark conversation as resolved"""
        self.status = 'resolved'
        self.unread_count = 0

    def _map_message_direction(self, msg_data):
        """Map message direction from API data"""
        action = msg_data.get('action', '')
        if action == 'incoming':
            return 'incoming'
        elif action == 'outgoing':
            return 'outgoing'

        # Fallback logic
        direction = msg_data.get('direction', '').lower()
        if direction in ['inbound', 'received', 'in']:
            return 'incoming'
        elif direction in ['outbound', 'sent', 'out']:
            return 'outgoing'

        return 'incoming'  # Default

    def _get_message_type(self, msg_data):
        """Get message type from API data"""
        data = msg_data.get('data', {})
        return data.get('type', 'text')

    def _extract_message_content(self, msg_data):
        """Extract message content from API data"""
        data = msg_data.get('data', {})

        # For text messages
        if isinstance(data, dict):
            context = data.get('context', {})
            if isinstance(context, dict):
                body = context.get('body', '')
                if body:
                    return body

        # Fallback methods
        for field in ['body', 'message', 'text', 'content']:
            value = msg_data.get(field, '')
            if value:
                return value

        return 'No content'

    def send_quick_message(self, message_text):
        """Send a quick message from the chat interface - Fixed duplicate prevention"""
        try:
            if not self.customer_contact:
                return {'success': False, 'message': 'No customer contact found'}

            # Use the chat config to send message
            if not self.config_id:
                return {'success': False, 'message': 'No chat configuration found'}

            result = self.config_id.send_message(
                self.customer_contact,
                message_text,
                use_template=False
            )

            if result.get('status') == 'success':
                # Generate unique message_id to prevent duplicates
                api_message_id = result.get('message_id')
                if not api_message_id:
                    api_message_id = f"manual_{int(datetime.now().timestamp() * 1000)}_{uuid.uuid4().hex[:8]}"

                # Check if message already exists
                existing_message = self.env['myoperator.message'].search([
                    ('message_id', '=', api_message_id)
                ], limit=1)

                if not existing_message:
                    try:
                        # Create message record
                        self.env['myoperator.message'].create({
                            'conversation_id': self.id,
                            'message_id': api_message_id,
                            'direction': 'outgoing',
                            'message_type': 'text',
                            'content': message_text,
                            'timestamp': fields.Datetime.now(),
                        })
                    except Exception as e:
                        _logger.warning(f"Failed to create message record: {str(e)}")
                        # Continue even if message record creation fails

                # Update conversation
                self.last_message_at = fields.Datetime.now()

                return {'success': True, 'message': 'Message sent successfully'}
            else:
                return {'success': False, 'message': result.get('message', 'Failed to send message')}

        except Exception as e:
            _logger.error(f"Error in send_quick_message: {str(e)}")
            return {'success': False, 'message': str(e)}

    # Add cron method for auto-assignment
    @api.model
    def cron_auto_assign_conversations(self):
        """Auto assign conversations based on rules"""
        # Implementation for auto-assignment logic
        unassigned_conversations = self.search([
            ('status', '=', 'open'),
            ('assigned_user_id', '=', False),
            ('unread_count', '>', 0)
        ])

        for conversation in unassigned_conversations:
            # Simple round-robin assignment
            available_users = self.env['res.users'].search([
                ('groups_id', 'in', self.env.ref('myoperator_integration.group_myoperator_agent').id)
            ])

            if available_users:
                # Assign to user with least conversations
                user_conversations = {}
                for user in available_users:
                    count = self.search_count([
                        ('assigned_user_id', '=', user.id),
                        ('status', 'in', ['open', 'assigned'])
                    ])
                    user_conversations[user.id] = count

                # Find user with minimum conversations
                min_user_id = min(user_conversations, key=user_conversations.get)
                conversation.write({
                    'assigned_user_id': min_user_id,
                    'status': 'assigned'
                })

        _logger.info(f"Auto-assigned {len(unassigned_conversations)} conversations")


class MyOperatorMessage(models.Model):
    _name = 'myoperator.message'
    _description = 'MyOperator Message'
    _order = 'timestamp asc'
    _rec_name = 'content'

    conversation_id = fields.Many2one('myoperator.conversation', string='Conversation',
                                      required=True, ondelete='cascade')
    message_id = fields.Char('Message ID', required=True, index=True)

    direction = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing')
    ], string='Direction', required=True)

    message_type = fields.Selection([
        ('text', 'Text'),
        ('image', 'Image'),
        ('document', 'Document'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('template', 'Template')
    ], string='Type', default='text')

    content = fields.Text('Content')
    timestamp = fields.Datetime('Timestamp', default=fields.Datetime.now)

    # Status fields
    read_status = fields.Boolean('Read', default=False)
    delivered_status = fields.Boolean('Delivered', default=False)

    # Media fields
    media_url = fields.Char('Media URL')
    media_filename = fields.Char('Media Filename')
    media_caption = fields.Text('Media Caption')

    _sql_constraints = [
        ('unique_message_id', 'unique(message_id)', 'Message ID must be unique!')
    ]

    @api.model
    def create(self, vals):
        """Override create to handle duplicate message_id gracefully"""
        message_id = vals.get('message_id')

        if message_id:
            # Check if message already exists
            existing = self.search([('message_id', '=', message_id)], limit=1)
            if existing:
                _logger.warning(f"Message with ID {message_id} already exists, skipping creation")
                return existing

        try:
            return super().create(vals)
        except Exception as e:
            if 'unique_message_id' in str(e) or 'duplicate key' in str(e):
                # Generate new unique message_id
                original_id = vals.get('message_id', 'unknown')
                new_id = f"{original_id}_{int(datetime.now().timestamp() * 1000)}"
                vals['message_id'] = new_id
                _logger.warning(f"Duplicate message_id {original_id}, using {new_id}")
                return super().create(vals)
            else:
                raise

    def mark_as_read(self):
        """Mark message as read"""
        self.read_status = True
        # Update conversation unread count
        if self.direction == 'incoming':
            self.conversation_id.unread_count = max(0, self.conversation_id.unread_count - 1)

    @api.model
    def cron_cleanup_old_messages(self):
        """Cleanup old messages based on retention policy"""
        # Delete messages older than 6 months
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=180)
        old_messages = self.search([
            ('timestamp', '<', cutoff_date),
            ('message_type', '!=', 'template')  # Keep template messages
        ])

        if old_messages:
            count = len(old_messages)
            old_messages.unlink()
            _logger.info(f"Cleaned up {count} old messages")


# Add message log model for tracking
class MyOperatorMessageLog(models.Model):
    _name = 'myoperator.message.log'
    _description = 'MyOperator Message Log'
    _order = 'timestamp desc'

    config_id = fields.Many2one('myoperator.chat.config', string='Configuration', required=True)
    phone_number = fields.Char('Phone Number', required=True)
    message_type = fields.Selection([
        ('text', 'Text'),
        ('template', 'Template')
    ], string='Message Type', required=True)
    template_name = fields.Char('Template Name')
    status = fields.Selection([
        ('attempted', 'Attempted'),
        ('success', 'Success'),
        ('failed', 'Failed')
    ], string='Status', required=True)
    error_message = fields.Text('Error Message')
    timestamp = fields.Datetime('Timestamp', default=fields.Datetime.now)

    # Add indexes for better performance
    _sql_constraints = [
        ('check_status', 'CHECK(status IN (\'attempted\', \'success\', \'failed\'))',
         'Status must be attempted, success, or failed')
    ]