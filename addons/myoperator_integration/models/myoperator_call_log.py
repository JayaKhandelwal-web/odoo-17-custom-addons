from odoo import models, fields, api, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class MyOperatorCallLog(models.Model):
    _name = 'myoperator.call.log'
    _description = 'MyOperator Call Log'
    _order = 'timestamp desc'
    _rec_name = 'display_name'

    config_id = fields.Many2one('myoperator.config', string='Configuration', required=True)
    call_id = fields.Char('Call ID', required=True, index=True)
    caller_number = fields.Char('Caller Number', index=True)
    called_number = fields.Char('Called Number', index=True)
    call_type = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
        ('internal', 'Internal'),
        ('conference', 'Conference')
    ], string='Call Type')
    duration = fields.Integer('Duration (seconds)')
    duration_formatted = fields.Char('Duration', compute='_compute_duration_formatted', store=True)
    timestamp = fields.Datetime('Call Time')
    status = fields.Selection([
        ('answered', 'Answered'),
        ('missed', 'Missed'),
        ('busy', 'Busy'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ], string='Call Status')
    recording_url = fields.Char('Recording URL')

    # Related partner information
    caller_partner_id = fields.Many2one('res.partner', string='Caller Contact',
                                        compute='_compute_partners', store=True)
    called_partner_id = fields.Many2one('res.partner', string='Called Contact',
                                        compute='_compute_partners', store=True)

    # Additional fields
    notes = fields.Text('Notes')
    callback_history = fields.Text('Callback History', readonly=True)
    synced_date = fields.Datetime('Synced Date', default=fields.Datetime.now)
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('unique_call_id_config', 'unique(call_id, config_id)',
         'Call ID must be unique per configuration!')
    ]

    @api.depends('duration')
    def _compute_duration_formatted(self):
        for record in self:
            if record.duration:
                minutes = record.duration // 60
                seconds = record.duration % 60
                record.duration_formatted = f"{minutes}:{seconds:02d}"
            else:
                record.duration_formatted = "0:00"

    @api.depends('caller_number', 'called_number')
    def _compute_partners(self):
        for record in self:
            # Find caller partner
            if record.caller_number:
                caller_partner = self.env['res.partner'].search([
                    '|', ('phone', 'ilike', record.caller_number[-10:]),
                    ('mobile', 'ilike', record.caller_number[-10:])
                ], limit=1)
                record.caller_partner_id = caller_partner.id if caller_partner else False
            else:
                record.caller_partner_id = False

            # Find called partner
            if record.called_number:
                called_partner = self.env['res.partner'].search([
                    '|', ('phone', 'ilike', record.called_number[-10:]),
                    ('mobile', 'ilike', record.called_number[-10:])
                ], limit=1)
                record.called_partner_id = called_partner.id if called_partner else False
            else:
                record.called_partner_id = False

    @api.depends('caller_number', 'called_number', 'call_type', 'timestamp')
    def _compute_display_name(self):
        for record in self:
            if record.call_type == 'inbound':
                name = f"📞 {record.caller_number or 'Unknown'} → {record.called_number or 'Unknown'}"
            elif record.call_type == 'outbound':
                name = f"📤 {record.caller_number or 'Unknown'} → {record.called_number or 'Unknown'}"
            else:
                name = f"{record.call_type or 'Unknown'}: {record.caller_number or 'Unknown'}"

            if record.timestamp:
                name += f" ({record.timestamp.strftime('%Y-%m-%d %H:%M')})"

            record.display_name = name

    def _log_callback(self, callback_number, source_number=None):
        """Log callback attempt to the callback history"""
        timestamp = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] Callback initiated to {callback_number}"
        if source_number:
            log_entry += f" from {source_number}"

        if self.callback_history:
            self.callback_history += f"\n{log_entry}"
        else:
            self.callback_history = log_entry

    def action_create_lead(self):
        """Create a lead from this call log"""
        if not self.caller_partner_id and self.caller_number:
            lead_vals = {
                'name': f"Call from {self.caller_number}",
                'phone': self.caller_number,
                'description': f"Lead created from call log on {self.timestamp}",
            }
            lead = self.env['crm.lead'].create(lead_vals)

            return {
                'type': 'ir.actions.act_window',
                'name': _('New Lead'),
                'res_model': 'crm.lead',
                'res_id': lead.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_view_recording(self):
        """Open call recording in new tab"""
        if self.recording_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.recording_url,
                'target': 'new',
            }

    def action_call_back(self):
        """Open MyOperator webcall interface with pre-filled number"""
        # Determine the number to call back
        callback_number = None
        if self.call_type == 'inbound' and self.caller_number:
            callback_number = self.caller_number
        elif self.call_type == 'outbound' and self.called_number:
            callback_number = self.called_number
        elif self.caller_number:
            callback_number = self.caller_number

        if not callback_number:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Phone Number'),
                    'message': _('No phone number available for callback.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Log the callback attempt
        self._log_callback(callback_number)
        _logger.info(f"Opening webcall interface for callback to {callback_number} from call {self.call_id}")

        # Clean the phone number (remove spaces, dashes, etc.)
        clean_number = ''.join(filter(str.isdigit, callback_number))
        if callback_number.startswith('+'):
            clean_number = '+' + clean_number

        # Build the webcall URL with the phone number parameter
        # Try different parameter names that MyOperator might accept
        webcall_url = f'https://in.app.myoperator.com/webcall?number={clean_number}'

        # Alternative parameter names you can try:
        # webcall_url = f'https://in.app.myoperator.com/webcall?phone={clean_number}'
        # webcall_url = f'https://in.app.myoperator.com/webcall?to={clean_number}'
        # webcall_url = f'https://in.app.myoperator.com/webcall?destination={clean_number}'

        return {
            'type': 'ir.actions.act_url',
            'url': webcall_url,
            'target': 'new',
        }

    def action_smart_callback(self):
        """Smart callback with API integration and fallback to webcall"""
        # Determine the number to call back
        callback_number = None
        if self.call_type == 'inbound' and self.caller_number:
            callback_number = self.caller_number
        elif self.call_type == 'outbound' and self.called_number:
            callback_number = self.called_number
        elif self.caller_number:
            callback_number = self.caller_number

        if not callback_number:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Phone Number'),
                    'message': _('No phone number available for callback.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        try:
            # Get active MyOperator configuration
            config = self.config_id or self.env['myoperator.config'].get_active_config()

            # Check if callback is enabled
            if not config.enable_callback:
                # Fallback to direct webcall interface
                return self._open_webcall_interface(callback_number)

            # Make API call to initiate callback
            result = config.make_callback(callback_number)

            if result.get('status') == 'success':
                # Log the callback attempt
                _logger.info(f"Callback initiated to {callback_number} for call {self.call_id}")
                self._log_callback(callback_number, config.callback_source_number)

                # Handle different callback methods - prioritize browser method
                if result.get('callback_url'):
                    # Open MyOperator webcall interface
                    return {
                        'type': 'ir.actions.act_url',
                        'url': result['callback_url'],
                        'target': 'new',
                    }
                elif result.get('method') == 'notification':
                    message = _('Please manually call %s using your MyOperator system') % callback_number
                else:
                    message = _('Callback to %s has been initiated successfully.') % callback_number

                # If no URL to open, show notification
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Callback Initiated'),
                        'message': message,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                # If API call fails, fallback to direct webcall interface
                _logger.warning(
                    f"API callback failed, falling back to webcall interface: {result.get('message', 'Unknown error')}")
                return self._open_webcall_interface(callback_number)

        except Exception as e:
            _logger.error(f"Callback error: {str(e)}, falling back to webcall interface")
            # Fallback to direct webcall interface
            return self._open_webcall_interface(callback_number)

    def _open_webcall_interface(self, callback_number):
        """Open MyOperator webcall interface as fallback"""
        self._log_callback(callback_number)
        webcall_url = 'https://in.app.myoperator.com/webcall'

        return {
            'type': 'ir.actions.act_url',
            'url': webcall_url,
            'target': 'new',
        }

    def action_advanced_callback(self):
        """Open advanced callback wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Advanced Callback'),
            'res_model': 'callback.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'default_call_log_id': self.id,
            }
        }