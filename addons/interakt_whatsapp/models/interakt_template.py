from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class InteraktTemplate(models.Model):
    _name = 'interakt.template'
    _description = 'Interakt WhatsApp Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Template Name', required=True, tracking=True,
                       help='Exact template code name from Interakt')
    display_name_field = fields.Char(string='Display Name', tracking=True,
                                     help='Friendly name for the template')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    # Template Details
    template_code = fields.Char(string='Template Code', required=True,
                                help='Exact template code from Interakt API')
    language_code = fields.Char(string='Language Code', default='en', required=True)
    description = fields.Text(string='Description')

    # Template Structure
    header_type = fields.Selection([
        ('TEXT', 'Text'),
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
        ('DOCUMENT', 'Document'),
    ], string='Header Type', default='TEXT')

    header_text = fields.Char(string='Header Text')
    body_text = fields.Text(string='Body Text', required=True,
                            help='Template body with {{1}}, {{2}}, etc. for variables')
    footer_text = fields.Char(string='Footer Text')

    # Variable Configuration
    body_variable_count = fields.Integer(string='Body Variables', default=0,
                                         help='Number of {{1}}, {{2}}, etc. in body')
    body_variable_names = fields.Char(string='Variable Names',
                                      help='Comma-separated names for variables (e.g., "Customer Name,Phone,Location")')

    # Example Values
    example_header_url = fields.Char(string='Example Header URL',
                                     help='Example image/video/document URL for testing')
    example_body_values = fields.Text(string='Example Body Values',
                                      help='JSON array of example values for variables\nExample: ["Raja Kumar", "8298913646", "Bhopal"]')

    # Usage Settings
    trigger_model = fields.Selection([
        ('fleet.booking', 'Fleet Booking'),
    ], string='Trigger Model', help='Model that triggers this template')

    trigger_field = fields.Char(string='Trigger Field',
                                help='Field that triggers sending (e.g., "state")')
    trigger_value = fields.Char(string='Trigger Value',
                                help='Value that triggers sending (e.g., "confirmed")')

    auto_send = fields.Boolean(string='Auto Send', default=False, tracking=True,
                               help='Automatically send when trigger conditions are met')

    # Statistics
    message_count = fields.Integer(string='Messages Sent',
                                   compute='_compute_message_count',
                                   store=False)
    success_count = fields.Integer(string='Successful',
                                   compute='_compute_message_count',
                                   store=False)
    failed_count = fields.Integer(string='Failed',
                                  compute='_compute_message_count',
                                  store=False)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.depends('name')
    def _compute_message_count(self):
        """Compute message statistics"""
        for template in self:
            logs = self.env['interakt.message.log'].search([
                ('template_id', '=', template.id)
            ])
            template.message_count = len(logs)
            template.success_count = len(logs.filtered(lambda l: l.status == 'sent'))
            template.failed_count = len(logs.filtered(lambda l: l.status == 'failed'))

    @api.constrains('body_variable_count')
    def _check_body_variable_count(self):
        """Validate body variable count"""
        for record in self:
            if record.body_variable_count < 0:
                raise ValidationError(_('Body variable count cannot be negative.'))

    def action_test_template(self):
        """Test sending this template"""
        self.ensure_one()

        config = self.env['interakt.config'].get_active_config()

        if not config.test_phone:
            raise ValidationError(_('Please configure a test phone number in Interakt settings.'))

        # Parse example body values
        body_values = None
        if self.example_body_values:
            try:
                import json
                body_values = json.loads(self.example_body_values)
            except:
                body_values = [self.example_body_values]

        # Send test message
        result = config.send_template_message(
            phone=config.test_phone,
            country_code=config.test_country_code,
            template_name=self.template_code,
            body_values=body_values,
            header_url=self.example_header_url,
            callback_data=f"test_{self.template_code}"
        )

        if result.get('status') == 'success':
            self.message_post(
                body=_('✅ Test message sent successfully!\nMessage ID: %s') % result.get('message_id'),
                message_type='notification'
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Test message sent successfully!'),
                    'type': 'success',
                }
            }
        else:
            error_msg = result.get('message', 'Unknown error')
            self.message_post(
                body=_('❌ Test message failed!\nError: %s') % error_msg,
                message_type='notification'
            )
            raise ValidationError(_('Test message failed!\n\nError: %s') % error_msg)

    def action_view_message_logs(self):
        """View message logs for this template"""
        self.ensure_one()
        return {
            'name': _('Message Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'interakt.message.log',
            'view_mode': 'tree,form',
            'domain': [('template_id', '=', self.id)],
            'context': {'default_template_id': self.id},
        }