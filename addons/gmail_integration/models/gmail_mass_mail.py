# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class GmailMassMail(models.Model):
    _name = 'gmail.mass.mail'
    _description = 'Gmail Mass Mail Campaign'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc, id desc'

    # Campaign Information
    name = fields.Char(
        string='Campaign Name',
        required=True,
        tracking=True,
        help='Name of the mass mail campaign'
    )
    description = fields.Text(
        string='Description',
        help='Campaign description and notes'
    )
    
    # Gmail Account
    account_id = fields.Many2one(
        'gmail.account',
        string='Gmail Account',
        required=True,
        help='Gmail account to send from'
    )
    
    # Email Content
    subject = fields.Char(
        string='Subject',
        required=True,
        help='Email subject line (supports variables)'
    )
    body_html = fields.Html(
        string='HTML Body',
        sanitize_attributes=False,
        help='HTML email body (supports variables)'
    )
    body_plain = fields.Text(
        string='Plain Text Body',
        help='Plain text email body (supports variables)'
    )
    
    # Template
    template_id = fields.Many2one(
        'gmail.template',
        string='Email Template',
        help='Template used for this campaign'
    )
    
    # Recipients
    recipient_ids = fields.One2many(
        'gmail.mass.mail.recipient',
        'campaign_id',
        string='Recipients',
        help='Campaign recipients'
    )
    contact_list_ids = fields.Many2many(
        'gmail.contact.list',
        'gmail_mass_mail_contact_list_rel',
        'campaign_id',
        'list_id',
        string='Contact Lists',
        help='Contact lists to send to'
    )
    
    # Scheduling
    schedule_date = fields.Datetime(
        string='Schedule Date',
        help='When to send the campaign (leave empty for immediate)'
    )
    send_now = fields.Boolean(
        string='Send Now',
        default=False,
        help='Send campaign immediately'
    )
    
    # Sending Configuration
    batch_size = fields.Integer(
        string='Batch Size',
        default=50,
        help='Number of emails to send per batch'
    )
    batch_delay = fields.Integer(
        string='Batch Delay (minutes)',
        default=5,
        help='Minutes to wait between batches'
    )
    max_retries = fields.Integer(
        string='Max Retries',
        default=3,
        help='Maximum retry attempts for failed emails'
    )
    
    # Campaign Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', tracking=True,
       help='Campaign status')
    
    # Statistics
    total_recipients = fields.Integer(
        string='Total Recipients',
        compute='_compute_campaign_stats',
        store=True,
        help='Total number of recipients'
    )
    sent_count = fields.Integer(
        string='Sent',
        compute='_compute_campaign_stats',
        store=True,
        help='Number of successfully sent emails'
    )
    delivered_count = fields.Integer(
        string='Delivered',
        compute='_compute_campaign_stats',
        store=True,
        help='Number of delivered emails'
    )
    opened_count = fields.Integer(
        string='Opened',
        compute='_compute_campaign_stats',
        store=True,
        help='Number of opened emails'
    )
    clicked_count = fields.Integer(
        string='Clicked',
        compute='_compute_campaign_stats',
        store=True,
        help='Number of emails with clicks'
    )
    bounced_count = fields.Integer(
        string='Bounced',
        compute='_compute_campaign_stats',
        store=True,
        help='Number of bounced emails'
    )
    failed_count = fields.Integer(
        string='Failed',
        compute='_compute_campaign_stats',
        store=True,
        help='Number of failed emails'
    )
    unsubscribed_count = fields.Integer(
        string='Unsubscribed',
        compute='_compute_campaign_stats',
        store=True,
        help='Number of unsubscribes from this campaign'
    )
    
    # Computed Rates
    delivery_rate = fields.Float(
        string='Delivery Rate (%)',
        compute='_compute_rates',
        help='Percentage of emails delivered'
    )
    open_rate = fields.Float(
        string='Open Rate (%)',
        compute='_compute_rates',
        help='Percentage of emails opened'
    )
    click_rate = fields.Float(
        string='Click Rate (%)',
        compute='_compute_rates',
        help='Percentage of emails clicked'
    )
    bounce_rate = fields.Float(
        string='Bounce Rate (%)',
        compute='_compute_rates',
        help='Percentage of emails bounced'
    )
    
    # Sending Progress
    sending_progress = fields.Float(
        string='Sending Progress (%)',
        compute='_compute_sending_progress',
        help='Percentage of emails sent'
    )
    estimated_completion = fields.Datetime(
        string='Estimated Completion',
        compute='_compute_estimated_completion',
        help='Estimated completion time'
    )
    
    # Dates
    sent_date = fields.Datetime(
        string='Sent Date',
        help='When campaign was sent'
    )
    completed_date = fields.Datetime(
        string='Completed Date',
        help='When campaign sending was completed'
    )
    
    @api.depends('recipient_ids', 'recipient_ids.state')
    def _compute_campaign_stats(self):
        for record in self:
            recipients = record.recipient_ids
            record.total_recipients = len(recipients)
            record.sent_count = len(recipients.filtered(lambda r: r.state == 'sent'))
            record.delivered_count = len(recipients.filtered(lambda r: r.state == 'delivered'))
            record.opened_count = len(recipients.filtered(lambda r: r.opened))
            record.clicked_count = len(recipients.filtered(lambda r: r.clicked))
            record.bounced_count = len(recipients.filtered(lambda r: r.state == 'bounced'))
            record.failed_count = len(recipients.filtered(lambda r: r.state == 'failed'))
            record.unsubscribed_count = len(recipients.filtered(lambda r: r.unsubscribed))
    
    @api.depends('total_recipients', 'delivered_count', 'opened_count', 
                 'clicked_count', 'bounced_count')
    def _compute_rates(self):
        for record in self:
            total = record.total_recipients
            if total > 0:
                record.delivery_rate = (record.delivered_count / total) * 100
                record.open_rate = (record.opened_count / total) * 100
                record.click_rate = (record.clicked_count / total) * 100
                record.bounce_rate = (record.bounced_count / total) * 100
            else:
                record.delivery_rate = 0
                record.open_rate = 0
                record.click_rate = 0
                record.bounce_rate = 0
    
    @api.depends('total_recipients', 'sent_count')
    def _compute_sending_progress(self):
        for record in self:
            if record.total_recipients > 0:
                record.sending_progress = (record.sent_count / record.total_recipients) * 100
            else:
                record.sending_progress = 0
    
    @api.depends('state', 'sending_progress', 'batch_size', 'batch_delay', 'total_recipients', 'sent_count')
    def _compute_estimated_completion(self):
        for record in self:
            if record.state == 'sending' and record.total_recipients > record.sent_count:
                remaining = record.total_recipients - record.sent_count
                batches_remaining = (remaining + record.batch_size - 1) // record.batch_size
                minutes_remaining = batches_remaining * record.batch_delay
                record.estimated_completion = fields.Datetime.now() + timedelta(minutes=minutes_remaining)
            else:
                record.estimated_completion = False
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Load template content"""
        if self.template_id:
            self.subject = self.template_id.subject
            self.body_html = self.template_id.body_html
            self.body_plain = self.template_id.body_plain
    
    @api.constrains('batch_size')
    def _check_batch_size(self):
        for record in self:
            if record.batch_size <= 0:
                raise ValidationError(_('Batch size must be greater than 0'))
            if record.batch_size > 100:
                raise ValidationError(_('Batch size cannot exceed 100 emails per batch'))
    
    @api.constrains('schedule_date')
    def _check_schedule_date(self):
        for record in self:
            if record.schedule_date and record.schedule_date < fields.Datetime.now():
                raise ValidationError(_('Schedule date cannot be in the past'))
    
    def action_load_recipients_from_lists(self):
        """Load recipients from selected contact lists"""
        self.ensure_one()
        
        if not self.contact_list_ids:
            raise UserError(_('Please select at least one contact list'))
        
        # Clear existing recipients
        self.recipient_ids.unlink()
        
        # Load contacts from lists
        recipients_to_create = []
        for contact_list in self.contact_list_ids:
            for contact in contact_list.contact_ids:
                if contact.email and contact.email not in [r.email for r in recipients_to_create]:
                    recipients_to_create.append({
                        'campaign_id': self.id,
                        'email': contact.email,
                        'name': contact.name,
                        'partner_id': contact.partner_id.id if contact.partner_id else False,
                    })
        
        # Create recipient records
        self.env['gmail.mass.mail.recipient'].create(recipients_to_create)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Recipients Loaded'),
                'message': _('Loaded %d recipients from contact lists') % len(recipients_to_create),
                'type': 'success',
            }
        }
    
    def action_test_send(self):
        """Send test email to current user"""
        self.ensure_one()
        
        if not self.subject or not (self.body_html or self.body_plain):
            raise UserError(_('Please set subject and body content before testing'))
        
        test_recipient = self.env['gmail.mass.mail.recipient'].create({
            'campaign_id': self.id,
            'email': self.env.user.email or self.env.user.login,
            'name': self.env.user.name,
            'is_test': True,
        })
        
        try:
            test_recipient._send_email()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test Email Sent'),
                    'message': _('Test email sent to %s') % test_recipient.email,
                    'type': 'success',
                }
            }
        except Exception as e:
            raise UserError(_('Test email failed: %s') % str(e))
    
    def action_schedule_campaign(self):
        """Schedule campaign for sending"""
        self.ensure_one()
        
        if not self.recipient_ids:
            raise UserError(_('Campaign has no recipients'))
        
        if not self.account_id:
            raise UserError(_('Please select a Gmail account'))
        
        if self.account_id.status != 'connected':
            raise UserError(_('Gmail account is not connected'))
        
        if self.schedule_date:
            self.state = 'scheduled'
        else:
            self.state = 'sending'
            self._start_sending()
    
    def action_send_now(self):
        """Send campaign immediately"""
        self.ensure_one()
        self.send_now = True
        self.schedule_date = False
        self.action_schedule_campaign()
    
    def action_cancel_campaign(self):
        """Cancel scheduled or sending campaign"""
        self.ensure_one()
        
        if self.state not in ['scheduled', 'sending']:
            raise UserError(_('Only scheduled or sending campaigns can be cancelled'))
        
        self.state = 'cancelled'
        
        # Cancel pending recipients
        pending_recipients = self.recipient_ids.filtered(lambda r: r.state == 'pending')
        pending_recipients.write({'state': 'cancelled'})
    
    # Missing Action Methods for Stat Buttons
    def action_view_recipients(self):
        """View all recipients for this campaign"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Campaign Recipients'),
            'res_model': 'gmail.mass.mail.recipient',
            'view_mode': 'tree,form',
            'domain': [('campaign_id', '=', self.id)],
            'context': {
                'default_campaign_id': self.id,
                'search_default_group_by_state': 1,
            },
        }
    
    def action_view_sent(self):
        """View sent recipients for this campaign"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sent Recipients'),
            'res_model': 'gmail.mass.mail.recipient',
            'view_mode': 'tree,form',
            'domain': [('campaign_id', '=', self.id), ('state', '=', 'sent')],
            'context': {'default_campaign_id': self.id},
        }
    
    def action_view_delivered(self):
        """View delivered recipients for this campaign"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Delivered Recipients'),
            'res_model': 'gmail.mass.mail.recipient',
            'view_mode': 'tree,form',
            'domain': [('campaign_id', '=', self.id), ('state', '=', 'delivered')],
            'context': {'default_campaign_id': self.id},
        }
    
    def action_view_opened(self):
        """View recipients who opened emails from this campaign"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Opened Recipients'),
            'res_model': 'gmail.mass.mail.recipient',
            'view_mode': 'tree,form',
            'domain': [('campaign_id', '=', self.id), ('opened', '=', True)],
            'context': {'default_campaign_id': self.id},
        }
    
    def _start_sending(self):
        """Start sending campaign"""
        self.ensure_one()
        
        self.state = 'sending'
        self.sent_date = fields.Datetime.now()
        
        # Queue first batch
        self._queue_next_batch()
    
    def _queue_next_batch(self):
        """Queue next batch of emails for sending"""
        self.ensure_one()
        
        pending_recipients = self.recipient_ids.filtered(lambda r: r.state == 'pending')
        
        if not pending_recipients:
            # All emails sent
            self.state = 'sent'
            self.completed_date = fields.Datetime.now()
            return
        
        # Get next batch
        batch = pending_recipients[:self.batch_size]
        
        # Send batch
        for recipient in batch:
            try:
                recipient._send_email()
            except Exception as e:
                _logger.error(f'Failed to send email to {recipient.email}: {str(e)}')
                recipient.write({
                    'state': 'failed',
                    'error_message': str(e),
                })
        
        # Schedule next batch if there are more recipients
        remaining = pending_recipients[self.batch_size:]
        if remaining:
            # Schedule next batch using cron job
            self.env.ref('gmail_integration.ir_cron_send_mass_mail_batch').sudo().write({
                'nextcall': fields.Datetime.now() + timedelta(minutes=self.batch_delay),
                'active': True,
            })
    
    def cron_send_scheduled_campaigns(self):
        """Cron job to send scheduled campaigns"""
        scheduled_campaigns = self.search([
            ('state', '=', 'scheduled'),
            ('schedule_date', '<=', fields.Datetime.now()),
        ])
        
        for campaign in scheduled_campaigns:
            try:
                campaign._start_sending()
            except Exception as e:
                _logger.error(f'Failed to start campaign {campaign.name}: {str(e)}')
                campaign.write({
                    'state': 'failed',
                    'completed_date': fields.Datetime.now(),
                })
    
    def cron_send_next_batch(self):
        """Cron job to send next batch of emails"""
        sending_campaigns = self.search([('state', '=', 'sending')])
        
        for campaign in sending_campaigns:
            try:
                campaign._queue_next_batch()
            except Exception as e:
                _logger.error(f'Failed to send batch for campaign {campaign.name}: {str(e)}')


class GmailMassMailRecipient(models.Model):
    _name = 'gmail.mass.mail.recipient'
    _description = 'Gmail Mass Mail Recipient'
    _rec_name = 'email'
    _order = 'create_date desc'

    # Campaign Reference
    campaign_id = fields.Many2one(
        'gmail.mass.mail',
        string='Campaign',
        required=True,
        ondelete='cascade',
        help='Associated mass mail campaign'
    )
    
    # Recipient Information
    email = fields.Char(
        string='Email',
        required=True,
        help='Recipient email address'
    )
    name = fields.Char(
        string='Name',
        help='Recipient name'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        help='Associated partner'
    )
    
    # Sending Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('bounced', 'Bounced'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending',
       help='Email sending status')
    
    # Gmail Information
    gmail_message_id = fields.Char(
        string='Gmail Message ID',
        help='Gmail message ID after sending'
    )
    
    # Tracking
    sent_date = fields.Datetime(
        string='Sent Date',
        help='When email was sent'
    )
    delivered_date = fields.Datetime(
        string='Delivered Date',
        help='When email was delivered'
    )
    opened_date = fields.Datetime(
        string='First Opened',
        help='When email was first opened'
    )
    clicked_date = fields.Datetime(
        string='First Clicked',
        help='When email was first clicked'
    )
    
    # Tracking Status
    opened = fields.Boolean(
        string='Opened',
        default=False,
        help='Whether email was opened'
    )
    clicked = fields.Boolean(
        string='Clicked',
        default=False,
        help='Whether email was clicked'
    )
    unsubscribed = fields.Boolean(
        string='Unsubscribed',
        default=False,
        help='Whether recipient unsubscribed'
    )
    
    # Error Handling
    retry_count = fields.Integer(
        string='Retry Count',
        default=0,
        help='Number of send attempts'
    )
    error_message = fields.Text(
        string='Error Message',
        help='Last error message'
    )
    
    # Test Email
    is_test = fields.Boolean(
        string='Test Email',
        default=False,
        help='Whether this is a test email'
    )
    
    def _send_email(self):
        """Send email to recipient"""
        self.ensure_one()
        
        if self.state != 'pending':
            return
        
        self.state = 'sending'
        self.retry_count += 1
        
        try:
            # Get rendered content with personalization
            variables = {
                'recipient_name': self.name or self.email,
                'recipient_email': self.email,
            }
            
            # Add partner-specific variables if available
            if self.partner_id:
                variables.update({
                    'partner_name': self.partner_id.name,
                    'partner_email': self.partner_id.email,
                    'partner_phone': self.partner_id.phone,
                    'partner_company': self.partner_id.parent_name or '',
                })
            
            # Render template content
            if self.campaign_id.template_id:
                rendered = self.campaign_id.template_id.get_rendered_content(variables)
                subject = rendered['subject']
                body_html = rendered['body_html']
                body_plain = rendered['body_plain']
            else:
                # Use campaign content directly
                subject = self.campaign_id.subject
                body_html = self.campaign_id.body_html
                body_plain = self.campaign_id.body_plain
                
                # Simple variable replacement
                for var_name, var_value in variables.items():
                    if subject:
                        subject = subject.replace(f'{{{{{var_name}}}}}', str(var_value))
                    if body_html:
                        body_html = body_html.replace(f'{{{{{var_name}}}}}', str(var_value))
                    if body_plain:
                        body_plain = body_plain.replace(f'{{{{{var_name}}}}}', str(var_value))
            
            # Send via Gmail API (implementation will be added)
            # For now, just mark as sent
            self.write({
                'state': 'sent',
                'sent_date': fields.Datetime.now(),
                'gmail_message_id': f'test_{self.id}',  # Placeholder
            })
            
            _logger.info(f'Email sent to {self.email} for campaign {self.campaign_id.name}')
            
        except Exception as e:
            error_msg = str(e)
            self.write({
                'state': 'failed',
                'error_message': error_msg,
            })
            _logger.error(f'Failed to send email to {self.email}: {error_msg}')
            raise
