# -*- coding: utf-8 -*-
import base64
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class GmailSendMail(models.TransientModel):
    _name = 'gmail.send.mail'
    _description = 'Gmail Send Mail Wizard'
    _rec_name = 'subject'

    # Basic Email Fields
    account_id = fields.Many2one(
        'gmail.account',
        string='Gmail Account',
        required=True,
        help='Select the Gmail account to send from',
        default=lambda self: self._get_default_account()
    )
    
    from_email = fields.Char(
        string='From',
        related='account_id.email_address',
        readonly=True
    )
    
    to_emails = fields.Text(
        string='To',
        required=True,
        help='Recipient email addresses (separate multiple with commas)'
    )
    
    cc_emails = fields.Text(
        string='CC',
        help='Carbon copy email addresses (separate multiple with commas)'
    )
    
    bcc_emails = fields.Text(
        string='BCC', 
        help='Blind carbon copy email addresses (separate multiple with commas)'
    )
    
    subject = fields.Char(
        string='Subject',
        required=True
    )
    
    body_html = fields.Html(
        string='Message',
        help='Email message content'
    )
    
    # Attachments
    attachment_ids = fields.One2many(
        'gmail.send.mail.attachment',
        'send_mail_id',
        string='Attachments'
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('failed', 'Failed')
    ], string='Status', default='draft', readonly=True)
    
    error_message = fields.Text(
        string='Error Message',
        readonly=True
    )
    
    # Computed Fields
    has_attachments = fields.Boolean(
        string='Has Attachments',
        compute='_compute_has_attachments'
    )

    @api.depends('attachment_ids')
    def _compute_has_attachments(self):
        for record in self:
            record.has_attachments = bool(record.attachment_ids)

    def _get_default_account(self):
        """Get default Gmail account"""
        account = self.env['gmail.account'].search([
            ('status', '=', 'connected')
        ], limit=1)
        return account.id if account else False

    @api.constrains('to_emails', 'cc_emails', 'bcc_emails')
    def _check_email_addresses(self):
        """Validate email addresses format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        for record in self:
            # Check TO emails
            if record.to_emails:
                emails = [email.strip() for email in record.to_emails.split(',')]
                for email_addr in emails:
                    if email_addr and not re.match(email_pattern, email_addr):
                        raise ValidationError(_('Invalid email address in TO field: %s') % email_addr)
            
            # Check CC emails
            if record.cc_emails:
                emails = [email.strip() for email in record.cc_emails.split(',')]
                for email_addr in emails:
                    if email_addr and not re.match(email_pattern, email_addr):
                        raise ValidationError(_('Invalid email address in CC field: %s') % email_addr)
            
            # Check BCC emails
            if record.bcc_emails:
                emails = [email.strip() for email in record.bcc_emails.split(',')]
                for email_addr in emails:
                    if email_addr and not re.match(email_pattern, email_addr):
                        raise ValidationError(_('Invalid email address in BCC field: %s') % email_addr)

    def send_email(self):
        """Send the email via Gmail API using existing OAuth setup"""
        self.ensure_one()
        
        if not self.account_id:
            raise UserError(_('Please select a Gmail account'))
        
        if not self.to_emails:
            raise UserError(_('Please enter at least one recipient'))
        
        if not self.subject:
            raise UserError(_('Please enter a subject'))
        
        try:
            # Use the existing Gmail API send method from account
            sent_message_id = self.account_id.send_email(
                to_emails=self._get_email_list(self.to_emails),
                subject=self.subject,
                body_html=self.body_html or '',
                body_plain=self._html_to_plain_text(self.body_html) if self.body_html else '',
                cc_emails=self._get_email_list(self.cc_emails) if self.cc_emails else None,
                bcc_emails=self._get_email_list(self.bcc_emails) if self.bcc_emails else None,
                attachments=self._prepare_attachments() if self.attachment_ids else None
            )
            
            # Update status
            self.write({
                'state': 'sent',
                'error_message': False
            })
            
            # Create sent message record
            self._create_sent_message_record(sent_message_id)
            
            # Close the wizard and show success notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Email Sent'),
                    'message': _('Your email has been sent successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            _logger.error('Failed to send email via Gmail API: %s', error_msg)
            
            self.write({
                'state': 'failed',
                'error_message': error_msg
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Send Failed'),
                    'message': _('Failed to send email: %s') % error_msg,
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def save_as_draft(self):
        """Save email as draft"""
        self.ensure_one()
        
        try:
            # Create draft message record
            self.env['gmail.message'].create({
                'gmail_message_id': f'draft_{self.id}_{datetime.now().timestamp()}',
                'account_id': self.account_id.id,
                'subject': self.subject or '(No Subject)',
                'from_email': self.account_id.email_address,
                'from_name': self.account_id.email_address,
                'to_emails': self.to_emails or '',
                'cc_emails': self.cc_emails or '',
                'bcc_emails': self.bcc_emails or '',
                'body_html': self.body_html or '',
                'date': fields.Datetime.now(),
                'direction': 'draft',
                'is_read': True,
                'sync_status': 'synced',
                'sync_date': fields.Datetime.now(),
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Draft Saved'),
                    'message': _('Your email has been saved as draft!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.warning('Failed to create draft record: %s', str(e))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Save Failed'),
                    'message': _('Failed to save draft: %s') % str(e),
                    'type': 'warning',
                    'sticky': False,
                }
            }

    def cancel(self):
        """Cancel compose and close wizard"""
        return {'type': 'ir.actions.act_window_close'}

    def _get_email_list(self, emails_text):
        """Convert comma-separated emails to list"""
        if not emails_text:
            return []
        return [email.strip() for email in emails_text.split(',') if email.strip()]

    def _prepare_attachments(self):
        """Prepare attachments for Gmail API"""
        attachments = []
        for attachment in self.attachment_ids:
            attachments.append({
                'filename': attachment.filename,
                'data': attachment.file_data,
                'mimetype': 'application/octet-stream'  # You can enhance this
            })
        return attachments

    def _html_to_plain_text(self, html_content):
        """Convert HTML to plain text"""
        if not html_content:
            return ''
        
        import re
        # Remove HTML tags
        clean = re.compile('<.*?>')
        plain_text = re.sub(clean, '', html_content)
        
        # Replace common HTML entities
        plain_text = plain_text.replace('&nbsp;', ' ')
        plain_text = plain_text.replace('&amp;', '&')
        plain_text = plain_text.replace('&lt;', '<')
        plain_text = plain_text.replace('&gt;', '>')
        
        return plain_text.strip()

    def _create_sent_message_record(self, gmail_message_id=None):
        """Create a record in gmail.message for sent email"""
        try:
            self.env['gmail.message'].create({
                'gmail_message_id': gmail_message_id or f'sent_{self.id}_{datetime.now().timestamp()}',
                'account_id': self.account_id.id,
                'subject': self.subject,
                'from_email': self.account_id.email_address,
                'from_name': self.account_id.email_address,
                'to_emails': self.to_emails,
                'cc_emails': self.cc_emails or '',
                'bcc_emails': self.bcc_emails or '',
                'body_html': self.body_html or '',
                'date': fields.Datetime.now(),
                'direction': 'outbound',
                'is_read': True,
                'sync_status': 'synced',
                'sync_date': fields.Datetime.now(),
            })
        except Exception as e:
            _logger.warning('Failed to create sent message record: %s', str(e))

    @api.model
    def create_reply(self, original_message_id, context=None):
        """Create reply email wizard"""
        original = self.env['gmail.message'].browse(original_message_id)
        
        return self.create({
            'account_id': original.account_id.id,
            'to_emails': original.from_email,
            'subject': f'Re: {original.subject}' if not original.subject.startswith('Re:') else original.subject,
            'body_html': self._get_reply_body(original),
        })

    @api.model  
    def create_forward(self, original_message_id, context=None):
        """Create forward email wizard"""
        original = self.env['gmail.message'].browse(original_message_id)
        
        return self.create({
            'account_id': original.account_id.id,
            'subject': f'Fwd: {original.subject}' if not original.subject.startswith('Fwd:') else original.subject,
            'body_html': self._get_forward_body(original),
        })

    def _get_reply_body(self, original_message):
        """Get formatted body for reply"""
        reply_body = '<br/><br/>'
        reply_body += f'On {original.date}, {original.from_name or original.from_email} wrote:<br/>'
        reply_body += '<blockquote style="margin: 0 0 0 .8ex; border-left: 1px #ccc solid; padding-left: 1ex;">'
        reply_body += original.body_html or original.body_plain or ''
        reply_body += '</blockquote>'
        return reply_body

    def _get_forward_body(self, original_message):
        """Get formatted body for forward"""
        forward_body = '<br/><br/>---------- Forwarded message ----------<br/>'
        forward_body += f'<b>From:</b> {original.from_name or original.from_email}<br/>'
        forward_body += f'<b>Date:</b> {original.date}<br/>'
        forward_body += f'<b>Subject:</b> {original.subject or "(No Subject)"}<br/>'
        forward_body += f'<b>To:</b> {original.to_emails}<br/>'
        if original.cc_emails:
            forward_body += f'<b>CC:</b> {original.cc_emails}<br/>'
        forward_body += f'<br/>{original.body_html or original.body_plain or ""}'
        return forward_body


class GmailSendMailAttachment(models.TransientModel):
    _name = 'gmail.send.mail.attachment'
    _description = 'Gmail Send Mail Attachment'

    send_mail_id = fields.Many2one(
        'gmail.send.mail',
        string='Send Mail',
        required=True,
        ondelete='cascade'
    )
    
    filename = fields.Char(
        string='File Name',
        required=True
    )
    
    file_data = fields.Binary(
        string='File',
        required=True,
        attachment=True
    )
    
    file_size = fields.Integer(
        string='File Size',
        compute='_compute_file_size',
        store=True
    )
    
    file_size_display = fields.Char(
        string='Size',
        compute='_compute_file_size_display'
    )
    
    @api.depends('file_data')
    def _compute_file_size(self):
        for record in self:
            if record.file_data:
                record.file_size = len(base64.b64decode(record.file_data))
            else:
                record.file_size = 0
    
    @api.depends('file_size')
    def _compute_file_size_display(self):
        for record in self:
            if record.file_size:
                if record.file_size < 1024:
                    record.file_size_display = f"{record.file_size}B"
                elif record.file_size < 1024 * 1024:
                    record.file_size_display = f"{record.file_size / 1024:.1f}KB"
                else:
                    record.file_size_display = f"{record.file_size / (1024 * 1024):.1f}MB"
            else:
                record.file_size_display = "0B"
