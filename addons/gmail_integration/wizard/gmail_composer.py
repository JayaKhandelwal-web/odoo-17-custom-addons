# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class GmailComposeMessage(models.TransientModel):
    _name = 'gmail.compose.message'
    _description = 'Gmail Compose Message Wizard'

    # Account and Template
    account_id = fields.Many2one(
        'gmail.account',
        string='Gmail Account',
        required=True,
        domain=[('status', '=', 'connected')],
        help='Gmail account to send from'
    )
    template_id = fields.Many2one(
        'gmail.template',
        string='Email Template',
        help='Template to use for this email'
    )
    
    # Email Content
    subject = fields.Char(
        string='Subject',
        required=True,
        help='Email subject line'
    )
    body_html = fields.Html(
        string='HTML Body',
        sanitize_attributes=False,
        help='HTML email body'
    )
    body_plain = fields.Text(
        string='Plain Text Body',
        help='Plain text email body'
    )
    
    # Recipients
    to_emails = fields.Text(
        string='To',
        required=True,
        help='Recipient email addresses (comma separated)'
    )
    cc_emails = fields.Text(
        string='CC',
        help='CC email addresses (comma separated)'
    )
    bcc_emails = fields.Text(
        string='BCC',
        help='BCC email addresses (comma separated)'
    )
    reply_to = fields.Char(
        string='Reply To',
        help='Reply-to email address'
    )
    
    # Message Options
    send_immediately = fields.Boolean(
        string='Send Immediately',
        default=True,
        help='Send email immediately or save as draft'
    )
    schedule_date = fields.Datetime(
        string='Schedule Date',
        help='Schedule email for later sending'
    )
    track_opens = fields.Boolean(
        string='Track Opens',
        default=True,
        help='Track when email is opened'
    )
    track_clicks = fields.Boolean(
        string='Track Clicks',
        default=True,
        help='Track when links are clicked'
    )
    
    # Attachments
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'gmail_compose_attachment_rel',
        'compose_id',
        'attachment_id',
        string='Attachments',
        help='Files to attach to the email'
    )
    
    # Thread Reference (for replies/forwards)
    original_message_id = fields.Many2one(
        'gmail.message',
        string='Original Message',
        help='Original message for reply/forward'
    )
    thread_id = fields.Many2one(
        'gmail.thread',
        string='Thread',
        help='Thread to reply to'
    )
    
    # Message Type
    message_type = fields.Selection([
        ('new', 'New Email'),
        ('reply', 'Reply'),
        ('reply_all', 'Reply All'),
        ('forward', 'Forward'),
    ], string='Message Type', default='new',
       help='Type of email message')
    
    # Template Variables
    variable_ids = fields.One2many(
        'gmail.compose.variable',
        'compose_id',
        string='Template Variables',
        help='Template variables and their values'
    )
    
    # Computed Fields
    attachment_count = fields.Integer(
        string='Attachment Count',
        compute='_compute_attachment_count',
        help='Number of attachments'
    )
    recipient_count = fields.Integer(
        string='Recipient Count',
        compute='_compute_recipient_count',
        help='Total number of recipients'
    )
    
    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)
    
    @api.depends('to_emails', 'cc_emails', 'bcc_emails')
    def _compute_recipient_count(self):
        for record in self:
            count = 0
            if record.to_emails:
                count += len([email.strip() for email in record.to_emails.split(',') if email.strip()])
            if record.cc_emails:
                count += len([email.strip() for email in record.cc_emails.split(',') if email.strip()])
            if record.bcc_emails:
                count += len([email.strip() for email in record.bcc_emails.split(',') if email.strip()])
            record.recipient_count = count
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Load template content and variables"""
        if self.template_id:
            # Load template content
            self.subject = self.template_id.subject
            self.body_html = self.template_id.body_html
            self.body_plain = self.template_id.body_plain
            self.to_emails = self.template_id.to_emails
            self.cc_emails = self.template_id.cc_emails
            self.bcc_emails = self.template_id.bcc_emails
            self.reply_to = self.template_id.reply_to
            
            # Load template variables
            self._load_template_variables()
    
    @api.onchange('original_message_id')
    def _onchange_original_message_id(self):
        """Set recipients and subject for reply/forward"""
        if self.original_message_id:
            original = self.original_message_id
            
            if self.message_type == 'reply':
                self.to_emails = original.from_email
                self.subject = f'Re: {original.subject}' if not original.subject.startswith('Re:') else original.subject
                
            elif self.message_type == 'reply_all':
                # Set to original sender
                self.to_emails = original.from_email
                
                # Add original recipients to CC (excluding current account)
                cc_emails = []
                if original.to_emails:
                    cc_emails.extend([email.strip() for email in original.to_emails.split(',') if email.strip()])
                if original.cc_emails:
                    cc_emails.extend([email.strip() for email in original.cc_emails.split(',') if email.strip()])
                
                # Remove account email from CC
                account_email = self.account_id.email_address
                cc_emails = [email for email in cc_emails if email != account_email]
                
                self.cc_emails = ', '.join(cc_emails) if cc_emails else ''
                self.subject = f'Re: {original.subject}' if not original.subject.startswith('Re:') else original.subject
                
            elif self.message_type == 'forward':
                self.subject = f'Fwd: {original.subject}' if not original.subject.startswith('Fwd:') else original.subject
                self.body_html = self._get_forward_body_html(original)
                self.body_plain = self._get_forward_body_plain(original)
            
            # Set thread reference
            self.thread_id = original.thread_id
    
    @api.constrains('to_emails', 'cc_emails', 'bcc_emails', 'reply_to')
    def _check_email_format(self):
        """Validate email address formats"""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        for record in self:
            # Check all email fields
            for field_name in ['to_emails', 'cc_emails', 'bcc_emails']:
                emails = getattr(record, field_name)
                if emails:
                    for email in emails.split(','):
                        email = email.strip()
                        if email and not email_pattern.match(email):
                            raise ValidationError(
                                _('Invalid email format in %s: %s') % (field_name, email)
                            )
            
            # Check reply-to
            if record.reply_to and not email_pattern.match(record.reply_to):
                raise ValidationError(_('Invalid Reply-To email format: %s') % record.reply_to)
    
    @api.constrains('schedule_date')
    def _check_schedule_date(self):
        for record in self:
            if record.schedule_date and record.schedule_date < fields.Datetime.now():
                raise ValidationError(_('Schedule date cannot be in the past'))
    
    def _load_template_variables(self):
        """Load template variables for user input"""
        if not self.template_id:
            return
        
        # Clear existing variables
        self.variable_ids.unlink()
        
        # Create variable records for user input
        variable_vals = []
        for template_var in self.template_id.variable_ids:
            variable_vals.append({
                'compose_id': self.id,
                'template_variable_id': template_var.id,
                'name': template_var.name,
                'description': template_var.description,
                'variable_type': template_var.variable_type,
                'is_required': template_var.is_required,
                'default_value': template_var.default_value,
                'sequence': template_var.sequence,
            })
        
        if variable_vals:
            self.env['gmail.compose.variable'].create(variable_vals)
    
    def _get_forward_body_html(self, original_message):
        """Get formatted HTML body for forwarding"""
        body = f"""
        <br/><br/>
        <div style="border-left: 2px solid #ccc; padding-left: 10px; margin-left: 10px;">
            <p><strong>---------- Forwarded message ----------</strong></p>
            <p><strong>From:</strong> {original_message.from_name or original_message.from_email}</p>
            <p><strong>Date:</strong> {original_message.date}</p>
            <p><strong>Subject:</strong> {original_message.subject or "(No Subject)"}</p>
            <p><strong>To:</strong> {original_message.to_emails}</p>
        """
        
        if original_message.cc_emails:
            body += f'<p><strong>CC:</strong> {original_message.cc_emails}</p>'
        
        body += f"""
            <br/>
            {original_message.body_html or original_message.body_plain or ""}
        </div>
        """
        
        return body
    
    def _get_forward_body_plain(self, original_message):
        """Get formatted plain text body for forwarding"""
        body = f"""


---------- Forwarded message ----------
From: {original_message.from_name or original_message.from_email}
Date: {original_message.date}
Subject: {original_message.subject or "(No Subject)"}
To: {original_message.to_emails}
"""
        
        if original_message.cc_emails:
            body += f'CC: {original_message.cc_emails}\n'
        
        body += f'\n{original_message.body_plain or original_message.body_html or ""}'
        
        return body
    
    def action_send_email(self):
        """Send the email"""
        self.ensure_one()
        
        # Validate required fields
        if not self.to_emails:
            raise UserError(_('Please specify at least one recipient'))
        
        if not self.subject:
            raise UserError(_('Please enter a subject'))
        
        if not self.body_html and not self.body_plain:
            raise UserError(_('Please enter email content'))
        
        # Check account status
        if self.account_id.status != 'connected':
            raise UserError(_('Gmail account is not connected'))
        
        try:
            # Render template variables if template is used
            if self.template_id:
                self._render_template_variables()
            
            # Send email via Gmail API
            message_data = self._prepare_message_data()
            gmail_message_id = self._send_via_gmail_api(message_data)
            
            # Create Gmail message record
            self._create_gmail_message_record(gmail_message_id, message_data)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Email Sent'),
                    'message': _('Your email has been sent successfully!'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f'Failed to send email: {str(e)}')
            raise UserError(_('Failed to send email: %s') % str(e))
    
    def action_save_draft(self):
        """Save email as draft"""
        self.ensure_one()
        
        try:
            # Render template variables if template is used
            if self.template_id:
                self._render_template_variables()
            
            # Save as draft via Gmail API
            message_data = self._prepare_message_data()
            gmail_message_id = self._save_draft_via_gmail_api(message_data)
            
            # Create Gmail message record
            message_data['is_draft'] = True
            self._create_gmail_message_record(gmail_message_id, message_data)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Draft Saved'),
                    'message': _('Your email has been saved as a draft'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f'Failed to save draft: {str(e)}')
            raise UserError(_('Failed to save draft: %s') % str(e))
    
    def action_schedule_email(self):
        """Schedule email for later sending"""
        self.ensure_one()
        
        if not self.schedule_date:
            raise UserError(_('Please set a schedule date'))
        
        # For now, save as draft and create a scheduled action
        # In full implementation, this would integrate with a job queue
        
        try:
            self.action_save_draft()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Email Scheduled'),
                    'message': _('Your email has been scheduled for %s') % self.schedule_date,
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f'Failed to schedule email: {str(e)}')
            raise UserError(_('Failed to schedule email: %s') % str(e))
    
    def _render_template_variables(self):
        """Render template variables in content"""
        variable_values = {}
        
        # Collect variable values
        for var in self.variable_ids:
            if var.is_required and not var.value:
                raise UserError(_('Required variable "%s" is not set') % var.name)
            variable_values[var.name] = var.value or var.default_value or ''
        
        # Add system variables
        system_variables = {
            'user_name': self.env.user.name,
            'company_name': self.env.company.name,
            'current_date': fields.Date.today().strftime('%Y-%m-%d'),
            'current_time': fields.Datetime.now().strftime('%H:%M:%S'),
        }
        variable_values.update(system_variables)
        
        # Render subject
        if self.subject:
            for var_name, var_value in variable_values.items():
                self.subject = self.subject.replace(f'{{{{{var_name}}}}}', str(var_value))
        
        # Render HTML body
        if self.body_html:
            for var_name, var_value in variable_values.items():
                self.body_html = self.body_html.replace(f'{{{{{var_name}}}}}', str(var_value))
        
        # Render plain body
        if self.body_plain:
            for var_name, var_value in variable_values.items():
                self.body_plain = self.body_plain.replace(f'{{{{{var_name}}}}}', str(var_value))
    
    def _prepare_message_data(self):
        """Prepare message data for Gmail API"""
        return {
            'account_id': self.account_id.id,
            'subject': self.subject,
            'body_html': self.body_html,
            'body_plain': self.body_plain,
            'to_emails': self.to_emails,
            'cc_emails': self.cc_emails,
            'bcc_emails': self.bcc_emails,
            'reply_to': self.reply_to,
            'thread_id': self.thread_id.id if self.thread_id else False,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
            'track_opens': self.track_opens,
            'track_clicks': self.track_clicks,
        }
    
    def _send_via_gmail_api(self, message_data):
        """Send email via Gmail API"""
        # This would implement actual Gmail API sending
        # For now, return a placeholder message ID
        
        _logger.info(f'Sending email via Gmail API: {message_data["subject"]}')
        
        # Placeholder implementation
        return f'gmail_msg_{self.id}_{fields.Datetime.now().timestamp()}'
    
    def _save_draft_via_gmail_api(self, message_data):
        """Save draft via Gmail API"""
        # This would implement actual Gmail API draft saving
        # For now, return a placeholder message ID
        
        _logger.info(f'Saving draft via Gmail API: {message_data["subject"]}')
        
        # Placeholder implementation
        return f'gmail_draft_{self.id}_{fields.Datetime.now().timestamp()}'
    
    def _create_gmail_message_record(self, gmail_message_id, message_data):
        """Create Gmail message record in Odoo"""
        message_vals = {
            'gmail_message_id': gmail_message_id,
            'account_id': message_data['account_id'],
            'subject': message_data['subject'],
            'body_html': message_data['body_html'],
            'body_plain': message_data['body_plain'],
            'from_email': self.account_id.email_address,
            'from_name': self.account_id.display_name or self.account_id.name,
            'to_emails': message_data['to_emails'],
            'cc_emails': message_data['cc_emails'],
            'bcc_emails': message_data['bcc_emails'],
            'reply_to': message_data['reply_to'],
            'date': fields.Datetime.now(),
            'direction': 'draft' if message_data.get('is_draft') else 'outbound',
            'is_draft': message_data.get('is_draft', False),
            'thread_id': message_data.get('thread_id'),
            'sync_status': 'synced',
            'sync_date': fields.Datetime.now(),
        }
        
        gmail_message = self.env['gmail.message'].create(message_vals)
        
        # Handle attachments if any
        if self.attachment_ids:
            for attachment in self.attachment_ids:
                self.env['gmail.attachment'].create({
                    'message_id': gmail_message.id,
                    'filename': attachment.name,
                    'mimetype': attachment.mimetype,
                    'size': len(attachment.datas) if attachment.datas else 0,
                    'content': attachment.datas,
                    'is_downloaded': True,
                    'download_date': fields.Datetime.now(),
                })
        
        return gmail_message


class GmailComposeVariable(models.TransientModel):
    _name = 'gmail.compose.variable'
    _description = 'Gmail Compose Template Variable'
    _order = 'sequence, name'

    compose_id = fields.Many2one(
        'gmail.compose.message',
        string='Compose Message',
        required=True,
        ondelete='cascade'
    )
    template_variable_id = fields.Many2one(
        'gmail.template.variable',
        string='Template Variable',
        required=True
    )
    name = fields.Char(
        string='Variable Name',
        required=True
    )
    description = fields.Text(
        string='Description'
    )
    variable_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('datetime', 'Date/Time'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('partner', 'Partner'),
        ('user', 'User'),
    ], string='Type', default='text')
    
    value = fields.Char(
        string='Value',
        help='Variable value for this email'
    )
    default_value = fields.Char(
        string='Default Value'
    )
    is_required = fields.Boolean(
        string='Required',
        default=False
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
