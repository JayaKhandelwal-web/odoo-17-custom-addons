from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CallbackWizard(models.TransientModel):
    _name = 'callback.wizard'
    _description = 'Callback Wizard'

    call_log_id = fields.Many2one('myoperator.call.log', string='Call Log', required=True)
    destination_number = fields.Char('Destination Number', required=True)
    source_number = fields.Char('Source Number', help='Leave empty to use default from configuration')
    config_id = fields.Many2one('myoperator.config', string='Configuration')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        # Get call log from context
        call_log_id = self.env.context.get('active_id')
        if call_log_id:
            call_log = self.env['myoperator.call.log'].browse(call_log_id)
            res['call_log_id'] = call_log_id
            res['config_id'] = call_log.config_id.id

            # Determine destination number based on call type
            if call_log.call_type == 'inbound' and call_log.caller_number:
                res['destination_number'] = call_log.caller_number
            elif call_log.call_type == 'outbound' and call_log.called_number:
                res['destination_number'] = call_log.called_number
            elif call_log.caller_number:
                res['destination_number'] = call_log.caller_number

            # Set default source number from config
            if call_log.config_id and call_log.config_id.callback_source_number:
                res['source_number'] = call_log.config_id.callback_source_number

        return res

    def action_make_callback(self):
        """Execute the callback"""
        if not self.destination_number:
            raise UserError(_('Destination number is required.'))

        config = self.config_id or self.env['myoperator.config'].get_active_config()

        # Use source number from wizard or config
        original_source = None
        if self.source_number and self.source_number != config.callback_source_number:
            # Temporarily override config source number
            original_source = config.callback_source_number
            config.callback_source_number = self.source_number

        try:
            result = config.make_callback(self.destination_number)

            if result.get('status') == 'success':
                # Log the callback in the call log using the simple logging method
                if self.call_log_id:
                    self.call_log_id._log_callback(
                        self.destination_number,
                        self.source_number or config.callback_source_number
                    )

                # Handle different callback methods
                if result.get('callback_url'):
                    # Open MyOperator webcall interface
                    return {
                        'type': 'ir.actions.act_url',
                        'url': result['callback_url'],
                        'target': 'new',
                    }
                elif result.get('method') == 'notification':
                    message = _('Please manually call %s using your MyOperator system') % self.destination_number
                else:
                    message = _('Callback to %s has been initiated successfully.') % self.destination_number

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
                raise UserError(_('Callback failed: %s') % result.get('message', 'Unknown error'))

        finally:
            # Restore original source number if it was temporarily changed
            if original_source is not None:
                config.callback_source_number = original_source