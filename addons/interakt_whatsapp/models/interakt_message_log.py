from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class InteraktMessageLog(models.Model):
    _name = 'interakt.message.log'
    _description = 'Interakt Message Log'
    _order = 'create_date desc'
    _rec_name = 'message_id'

    message_id = fields.Char(string='Message ID', readonly=True)
    config_id = fields.Many2one('interakt.config', string='Configuration',
                                readonly=True, ondelete='cascade')
    template_id = fields.Many2one('interakt.template', string='Template',
                                  readonly=True, ondelete='set null')

    # Recipient Details
    phone_number = fields.Char(string='Phone Number', readonly=True)
    country_code = fields.Char(string='Country Code', readonly=True)
    recipient_name = fields.Char(string='Recipient Name', readonly=True)

    # Message Details
    template_name = fields.Char(string='Template Name', readonly=True)
    body_values = fields.Text(string='Body Values', readonly=True)
    header_url = fields.Char(string='Header URL', readonly=True)
    callback_data = fields.Char(string='Callback Data', readonly=True)

    # Status
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ], string='Status', default='pending', readonly=True, tracking=True)

    error_message = fields.Text(string='Error Message', readonly=True)

    # Related Record
    model_name = fields.Char(string='Related Model', readonly=True)
    res_id = fields.Integer(string='Related Record ID', readonly=True)

    # Timestamps
    sent_date = fields.Datetime(string='Sent Date', readonly=True)
    delivered_date = fields.Datetime(string='Delivered Date', readonly=True)
    read_date = fields.Datetime(string='Read Date', readonly=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 readonly=True)

    def name_get(self):
        """Custom name_get to show meaningful information"""
        result = []
        for record in self:
            name = f"{record.template_name or 'Message'} - {record.phone_number} ({record.status})"
            result.append((record.id, name))
        return result

    def action_open_related_record(self):
        """Open the related record"""
        self.ensure_one()
        if self.model_name and self.res_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': self.model_name,
                'res_id': self.res_id,
                'view_mode': 'form',
                'target': 'current',
            }