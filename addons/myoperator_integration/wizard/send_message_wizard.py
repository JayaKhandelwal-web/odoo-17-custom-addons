from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SendMessageWizard(models.TransientModel):
    _name = 'myoperator.send.message.wizard'
    _description = 'Send Message Wizard'

    conversation_id = fields.Many2one('myoperator.conversation', string='Conversation')
    phone_number = fields.Char('Phone Number', required=True)
    message_text = fields.Text('Message', required=False)

    message_type = fields.Selection([
        ('text', 'Text Message'),
        ('template', 'Template Message')
    ], string='Message Type', default='text')

    template_name = fields.Char('Template Name', help='Required for template messages')

    # Template selection fields
    available_templates = fields.Text('Available Templates', readonly=True)
    template_selection = fields.Selection('_get_template_selection', string='Select Template')

    # Template parameters (for dynamic templates)
    template_parameters = fields.Text('Template Parameters (JSON)',
                                      help='For templates with variables, provide parameters as JSON')

    @api.model
    def _get_template_selection(self):
        """Get template selection options"""
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
            template_selection_list = []

            for template in templates:
                template_name = template.get('name', 'Unknown')
                template_status = template.get('status', 'Unknown')

                # Only add approved/active templates to selection
                if template_status.lower() in ['approved', 'active']:
                    template_selection_list.append((template_name, template_name))

            # Return default if no templates found
            if not template_selection_list:
                template_selection_list = [('hello_world', 'hello_world')]

            return template_selection_list

        except Exception as e:
            # Fallback in case of any error
            return [('hello_world', 'hello_world')]

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
                template_list = []
                template_selection_list = []

                for template in templates:
                    template_name = template.get('name', 'Unknown')
                    template_status = template.get('status', 'Unknown')
                    template_list.append(f"- {template_name} ({template_status})")

                    # Only add approved templates to selection
                    if template_status.lower() in ['approved', 'active']:
                        template_selection_list.append((template_name, template_name))

                res['available_templates'] = '\n'.join(template_list) if template_list else 'No templates available'

                # Don't update selection field here - it's handled by _get_template_selection method
        else:
            # Try to get default config for templates
            default_config = self.env['myoperator.chat.config'].get_active_config()
            if default_config:
                templates = default_config.get_available_templates()
                template_list = []
                template_selection_list = []

                for template in templates:
                    template_name = template.get('name', 'Unknown')
                    template_status = template.get('status', 'Unknown')
                    template_list.append(f"- {template_name} ({template_status})")

                    if template_status.lower() in ['approved', 'active']:
                        template_selection_list.append((template_name, template_name))

                res['available_templates'] = '\n'.join(template_list) if template_list else 'No templates available'

        return res

    @api.onchange('message_type')
    def _onchange_message_type(self):
        """Clear fields when message type changes"""
        if self.message_type == 'text':
            self.template_name = False
            self.template_selection = False
            self.template_parameters = False
        elif self.message_type == 'template':
            self.message_text = False

    @api.onchange('template_selection')
    def _onchange_template_selection(self):
        """Update template_name when selection changes"""
        if self.template_selection:
            self.template_name = self.template_selection

    def action_send_message(self):
        """Send the message"""
        if not self.phone_number:
            raise UserError(_('Phone number is required.'))

        # Validate based on message type
        if self.message_type == 'text':
            if not self.message_text:
                raise UserError(_('Message text is required for text messages.'))
        elif self.message_type == 'template':
            if not self.template_name and not self.template_selection:
                raise UserError(_('Template name is required for template messages.'))

            # Use template_selection if available, otherwise use template_name
            template_to_use = self.template_selection or self.template_name

            if not template_to_use:
                raise UserError(_('Please select a template or enter a template name.'))

        # Get chat configuration
        if self.conversation_id:
            config = self.conversation_id.config_id
        else:
            config = self.env['myoperator.chat.config'].get_active_config()

        if not config:
            raise UserError(_('No chat configuration found. Please configure MyOperator settings first.'))

        try:
            # Send message based on type
            if self.message_type == 'template':
                template_to_use = self.template_selection or self.template_name

                # Parse template parameters if provided
                template_params = None
                if self.template_parameters:
                    try:
                        import json
                        template_params = json.loads(self.template_parameters)
                    except json.JSONDecodeError:
                        raise UserError(_('Invalid JSON format in template parameters.'))

                result = config.send_message(
                    self.phone_number,
                    '',  # Empty message for templates
                    use_template=True,
                    template_name=template_to_use,
                    template_parameters=template_params
                )
            else:
                result = config.send_message(
                    self.phone_number,
                    self.message_text,
                    use_template=False
                )

            if result.get('status') == 'success':
                # Create message record if conversation exists
                if self.conversation_id:
                    if self.message_type == 'text':
                        message_content = self.message_text
                    else:
                        message_content = f'Template: {template_to_use}'
                        if template_params:
                            message_content += f' (with parameters)'

                    self.env['myoperator.message'].create({
                        'conversation_id': self.conversation_id.id,
                        'message_id': result.get('message_id', 'temp_' + str(fields.Datetime.now().timestamp())),
                        'direction': 'outgoing',
                        'message_type': self.message_type,
                        'content': message_content,
                        'timestamp': fields.Datetime.now(),
                    })

                    # Update conversation
                    self.conversation_id.last_message_at = fields.Datetime.now()

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Message Sent'),
                        'message': _('Message sent successfully!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_msg = result.get('message', 'Unknown error')
                if '24 hour' in error_msg.lower():
                    error_msg += '\n\nTip: Try using a template message for conversations older than 24 hours.'

                raise UserError(_('Failed to send message: %s') % error_msg)

        except Exception as e:
            raise UserError(_('Error sending message: %s') % str(e))

    def action_send_template(self):
        """Quick action to send template message"""
        self.message_type = 'template'
        if not self.template_name and not self.template_selection:
            # Use default template if none selected
            self.template_name = 'hello_world'
        return self.action_send_message()

    def action_refresh_templates(self):
        """Refresh available templates"""
        if self.conversation_id and self.conversation_id.config_id:
            config = self.conversation_id.config_id
        else:
            config = self.env['myoperator.chat.config'].get_active_config()

        if config:
            templates = config.get_available_templates()
            template_list = []

            for template in templates:
                template_name = template.get('name', 'Unknown')
                template_status = template.get('status', 'Unknown')
                template_list.append(f"- {template_name} ({template_status})")

            self.available_templates = '\n'.join(template_list) if template_list else 'No templates available'

            # Force refresh of the selection field by triggering a recompute
            self.template_selection = False

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Templates Refreshed'),
                    'message': _('Template list has been updated. The form will reload to show new templates.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError(_('No chat configuration found.'))