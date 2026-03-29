from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError


class SyncCallLogsWizard(models.TransientModel):
    _name = 'sync.call.logs.wizard'
    _description = 'Sync Call Logs Wizard'

    config_id = fields.Many2one('myoperator.config', string='Configuration',
                               default=lambda self: self._get_default_config(),
                               required=True)
    date_from = fields.Datetime('Date From',
                               default=lambda self: fields.Datetime.now() - timedelta(days=7))
    date_to = fields.Datetime('Date To', default=fields.Datetime.now)
    limit = fields.Integer('Limit', default=100, help='Maximum number of logs to sync')

    @api.model
    def _get_default_config(self):
        return self.env['myoperator.config'].search([('active', '=', True)], limit=1)

    def action_sync(self):
        """Perform the sync operation"""
        if not self.config_id:
            raise UserError(_('Please select a configuration.'))

        result = self.config_id.sync_call_logs(
            date_from=self.date_from.strftime('%Y-%m-%d %H:%M:%S') if self.date_from else None,
            date_to=self.date_to.strftime('%Y-%m-%d %H:%M:%S') if self.date_to else None,
            limit=self.limit
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Complete'),
                'message': _('Synced %d new call logs out of %d total logs.') % (
                    result['synced_count'], result['total_logs']
                ),
                'type': 'success',
                'sticky': True,
            }
        }