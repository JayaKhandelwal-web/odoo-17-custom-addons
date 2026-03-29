from odoo import models, fields, api, _
import re
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # MyOperator related fields
    myoperator_call_count = fields.Integer('MyOperator Calls',
                                           compute='_compute_myoperator_calls')
    last_call_date = fields.Datetime('Last Call Date',
                                     compute='_compute_myoperator_calls')
    
    # Chat related fields
    myoperator_conversation_count = fields.Integer('WhatsApp Conversations',
                                                   compute='_compute_myoperator_conversations')
    last_chat_date = fields.Datetime('Last Chat Date',
                                     compute='_compute_myoperator_conversations')
    
    # Total communication count
    total_communications = fields.Integer('Total Communications',
                                          compute='_compute_total_communications')

    def _compute_myoperator_calls(self):
        for partner in self:
            # Search for calls where this partner is either caller or called
            phone_numbers = []
            if partner.phone:
                phone_numbers.append(partner.phone)
            if partner.mobile:
                phone_numbers.append(partner.mobile)

            if phone_numbers:
                # Clean phone numbers (remove spaces, dashes, etc.)
                clean_numbers = [re.sub(r'[^\d+]', '', num)[-10:] for num in phone_numbers if num]

                domain = []
                for number in clean_numbers:
                    domain.extend([
                        '|', ('caller_number', 'ilike', number),
                        ('called_number', 'ilike', number),
                    ])

                if domain:
                    # Remove the first '|' operator
                    domain = domain[1:]

                    call_logs = self.env['myoperator.call.log'].search(domain)
                    partner.myoperator_call_count = len(call_logs)
                    partner.last_call_date = call_logs[0].timestamp if call_logs else False
                else:
                    partner.myoperator_call_count = 0
                    partner.last_call_date = False
            else:
                partner.myoperator_call_count = 0
                partner.last_call_date = False

    def _compute_myoperator_conversations(self):
        for partner in self:
            # Search for conversations where this partner is the customer
            phone_numbers = []
            if partner.phone:
                phone_numbers.append(partner.phone)
            if partner.mobile:
                phone_numbers.append(partner.mobile)

            if phone_numbers:
                # Clean phone numbers
                clean_numbers = [re.sub(r'[^\d+]', '', num)[-10:] for num in phone_numbers if num]

                domain = []
                for number in clean_numbers:
                    domain.extend([
                        '|', ('customer_contact', 'ilike', number),
                        ('partner_id', '=', partner.id),
                    ])

                if domain:
                    domain = domain[1:]  # Remove first '|'

                    conversations = self.env['myoperator.conversation'].search(domain)
                    partner.myoperator_conversation_count = len(conversations)
                    partner.last_chat_date = conversations[0].last_message_at if conversations else False
                else:
                    partner.myoperator_conversation_count = 0
                    partner.last_chat_date = False
            else:
                partner.myoperator_conversation_count = 0
                partner.last_chat_date = False

    @api.depends('myoperator_call_count', 'myoperator_conversation_count')
    def _compute_total_communications(self):
        for partner in self:
            partner.total_communications = partner.myoperator_call_count + partner.myoperator_conversation_count

    def action_view_call_logs(self):
        """View call logs for this partner"""
        phone_numbers = []
        if self.phone:
            phone_numbers.append(self.phone)
        if self.mobile:
            phone_numbers.append(self.mobile)

        if not phone_numbers:
            return

        # Clean phone numbers
        clean_numbers = [re.sub(r'[^\d+]', '', num)[-10:] for num in phone_numbers if num]

        domain = []
        for number in clean_numbers:
            domain.extend([
                '|', ('caller_number', 'ilike', number),
                ('called_number', 'ilike', number),
            ])

        if domain:
            domain = domain[1:]  # Remove first '|'

            return {
                'type': 'ir.actions.act_window',
                'name': f'Call Logs - {self.name}',
                'res_model': 'myoperator.call.log',
                'view_mode': 'tree,form',
                'domain': domain,
                'context': {'default_partner_id': self.id},
            }

    def action_view_conversations(self):
        """View WhatsApp conversations for this partner"""
        phone_numbers = []
        if self.phone:
            phone_numbers.append(self.phone)
        if self.mobile:
            phone_numbers.append(self.mobile)

        if not phone_numbers:
            return

        # Clean phone numbers
        clean_numbers = [re.sub(r'[^\d+]', '', num)[-10:] for num in phone_numbers if num]

        domain = []
        for number in clean_numbers:
            domain.extend([
                '|', ('customer_contact', 'ilike', number),
                ('partner_id', '=', self.id),
            ])

        if domain:
            domain = domain[1:]  # Remove first '|'

            return {
                'type': 'ir.actions.act_window',
                'name': f'WhatsApp Conversations - {self.name}',
                'res_model': 'myoperator.conversation',
                'view_mode': 'tree,form',
                'domain': domain,
                'context': {'default_partner_id': self.id},
            }

    def action_send_whatsapp_message(self):
        """Send WhatsApp message to this partner"""
        if not (self.phone or self.mobile):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Phone Number'),
                    'message': _('No phone number found for this contact.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Get the primary phone number (prefer mobile over phone)
        phone_number = self.mobile or self.phone

        return {
            'type': 'ir.actions.act_window',
            'name': _('Send WhatsApp Message'),
            'res_model': 'myoperator.send.message.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_phone_number': phone_number,
            }
        }

    def action_make_call(self):
        """Initiate call through MyOperator webcall interface"""
        if not (self.phone or self.mobile):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Phone Number'),
                    'message': _('No phone number found for this contact.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Get the primary phone number (prefer mobile over phone)
        phone_number = self.mobile or self.phone

        # Clean the phone number (remove spaces, dashes, etc.)
        clean_number = ''.join(filter(str.isdigit, phone_number))
        if phone_number.startswith('+'):
            clean_number = '+' + clean_number

        # Log the call attempt
        _logger.info(f"Initiating call to {phone_number} for partner {self.name} (ID: {self.id})")

        # Build the webcall URL with the phone number parameter
        webcall_url = f'https://in.app.myoperator.com/webcall?number={clean_number}'

        return {
            'type': 'ir.actions.act_url',
            'url': webcall_url,
            'target': 'new',
        }

    def action_communication_center(self):
        """Open communication center showing all interactions"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Communication Center - {self.name}',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('myoperator_integration.view_partner_communication_center').id,
            'target': 'current',
        }

    def action_smart_call(self):
        """Smart call with API integration and fallback to webcall"""
        if not (self.phone or self.mobile):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Phone Number'),
                    'message': _('No phone number found for this contact.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        phone_number = self.mobile or self.phone

        try:
            # Try to get active MyOperator configuration
            config = self.env['myoperator.config'].get_active_config()

            if not config or not config.enable_callback:
                # Fallback to direct webcall interface
                return self._open_webcall_interface(phone_number)

            # Make API call to initiate callback
            result = config.make_callback(phone_number)

            if result.get('status') == 'success':
                _logger.info(f"API call initiated to {phone_number} for partner {self.name}")

                if result.get('callback_url'):
                    return {
                        'type': 'ir.actions.act_url',
                        'url': result['callback_url'],
                        'target': 'new',
                    }
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Call Initiated'),
                            'message': _('Call to %s has been initiated successfully.') % phone_number,
                            'type': 'success',
                            'sticky': False,
                        }
                    }
            else:
                # If API call fails, fallback to webcall interface
                _logger.warning(
                    f"API call failed, falling back to webcall interface: {result.get('message', 'Unknown error')}")
                return self._open_webcall_interface(phone_number)

        except Exception as e:
            _logger.error(f"Smart call error: {str(e)}, falling back to webcall interface")
            return self._open_webcall_interface(phone_number)

    def _open_webcall_interface(self, phone_number):
        """Helper method to open MyOperator webcall interface"""
        # Clean the phone number
        clean_number = ''.join(filter(str.isdigit, phone_number))
        if phone_number.startswith('+'):
            clean_number = '+' + clean_number

        webcall_url = f'https://in.app.myoperator.com/webcall?number={clean_number}'

        return {
            'type': 'ir.actions.act_url',
            'url': webcall_url,
            'target': 'new',
        }