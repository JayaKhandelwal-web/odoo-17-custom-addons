# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)


class GmailMessage(models.Model):
    _name = 'gmail.message'
    _description = 'Gmail Message'
    _rec_name = 'subject'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Gmail Identifiers
    gmail_message_id = fields.Char(
        string='Gmail Message ID',
        required=True,
        index=True,
        help='Unique Gmail message identifier'
    )
    gmail_thread_id = fields.Char(
        string='Gmail Thread ID',
        index=True,
        help='Gmail thread identifier for conversation grouping'
    )
    
    # Account Reference
    account_id = fields.Many2one(
        'gmail.account',
        string='Gmail Account',
        required=True,
        ondelete='cascade',
        help='Associated Gmail account'
    )
    
    # Thread Reference
    thread_id = fields.Many2one(
        'gmail.thread',
        string='Thread',
        ondelete='set null',
        help='Associated conversation thread'
    )
    
    # Message Headers
    subject = fields.Char(
        string='Subject',
        index=True,
        help='Email subject line'
    )
    from_email = fields.Char(
        string='From',
        required=True,
        index=True,
        help='Sender email address'
    )
    from_name = fields.Char(
        string='From Name',
        help='Sender display name'
    )
    to_emails = fields.Text(
        string='To',
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
    
    # Message Content
    snippet = fields.Text(
        string='Snippet',
        help='Short preview of message content'
    )
    body_plain = fields.Html(
        string='Plain Text Body',
        help='Plain text version of email body'
    )
    body_html = fields.Html(
        string='HTML Body',
        sanitize_attributes=False,
        help='HTML version of email body'
    )
    
    # Message Metadata
    date = fields.Datetime(
        string='Date',
        required=True,
        index=True,
        help='Message date and time'
    )
    message_size = fields.Integer(
        string='Size (bytes)',
        help='Message size in bytes'
    )
    
    # Message Status
    is_read = fields.Boolean(
        string='Read',
        default=False,
        help='Whether message has been read'
    )
    is_starred = fields.Boolean(
        string='Starred',
        default=False,
        help='Whether message is starred'
    )
    is_important = fields.Boolean(
        string='Important',
        default=False,
        help='Whether message is marked as important'
    )
    is_draft = fields.Boolean(
        string='Draft',
        default=False,
        help='Whether message is a draft'
    )
    
    # Message Direction
    direction = fields.Selection([
        ('inbound', 'Incoming'),
        ('outbound', 'Outgoing'),
        ('draft', 'Draft'),
    ], string='Direction', required=True, default='inbound',
       help='Message direction')
    
    # Gmail Labels
    gmail_labels = fields.Text(
        string='Gmail Labels',
        help='Gmail labels as JSON string'
    )
    label_ids = fields.Char(
        string='Label IDs',
        help='Gmail label IDs (comma separated)'
    )
    
    # Sync Information
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('error', 'Error'),
    ], string='Sync Status', default='pending',
       help='Synchronization status')
    
    sync_date = fields.Datetime(
        string='Sync Date',
        help='When message was synced to Odoo'
    )
    last_updated = fields.Datetime(
        string='Last Updated',
        default=fields.Datetime.now,
        help='Last update timestamp'
    )
    
    # Relations
    attachment_ids = fields.One2many(
        'gmail.attachment',
        'message_id',
        string='Attachments',
        help='Message attachments'
    )
    
    # Partner Relations
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        help='Associated partner from sender email'
    )
    
    # Computed Fields
    attachment_count = fields.Integer(
        string='Attachment Count',
        compute='_compute_attachment_count',
        help='Number of attachments'
    )
    has_attachments = fields.Boolean(
        string='Has Attachments',
        compute='_compute_has_attachments',
        help='Whether message has attachments'
    )
    display_name_custom = fields.Char(
        string='Display Name',
        compute='_compute_display_name_custom',
        help='Custom display name for message'
    )
    
    # Constraints
    _sql_constraints = [
        ('unique_gmail_message', 'unique(gmail_message_id, account_id)', 
         'Gmail message ID must be unique per account!'),
    ]
    
    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)
    
    @api.depends('attachment_ids')
    def _compute_has_attachments(self):
        for record in self:
            record.has_attachments = bool(record.attachment_ids)
    
    @api.depends('subject', 'from_email', 'date')
    def _compute_display_name_custom(self):
        for record in self:
            if record.subject:
                display_name = record.subject[:50]
                if len(record.subject) > 50:
                    display_name += '...'
            else:
                display_name = _('(No Subject)')
            
            if record.from_email:
                display_name += f' - {record.from_email}'
            
            record.display_name_custom = display_name
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'sync_date' not in vals:
                vals['sync_date'] = fields.Datetime.now()
            if 'sync_status' not in vals:
                vals['sync_status'] = 'synced'
        return super().create(vals_list)
    
    def write(self, vals):
        if any(key in vals for key in ['is_read', 'is_starred', 'is_important', 'gmail_labels']):
            vals['last_updated'] = fields.Datetime.now()
        return super().write(vals)
    
    def action_mark_read(self):
        """Mark message as read"""
        self.ensure_one()
        if not self.is_read:
            self.is_read = True
            # Sync with Gmail API
            self._sync_read_status()
    
    def action_mark_unread(self):
        """Mark message as unread"""
        self.ensure_one()
        if self.is_read:
            self.is_read = False
            # Sync with Gmail API
            self._sync_read_status()
    
    def action_star(self):
        """Star message"""
        self.ensure_one()
        self.is_starred = True
        # Sync with Gmail API
        self._sync_star_status()
    
    def action_unstar(self):
        """Unstar message"""
        self.ensure_one()
        self.is_starred = False
        # Sync with Gmail API
        self._sync_star_status()
    
    def action_reply(self):
        """Open reply composer using send mail wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reply'),
            'res_model': 'gmail.send.mail',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_account_id': self.account_id.id,
                'default_to_emails': self.from_email,
                'default_subject': f'Re: {self.subject or ""}',
                'is_reply': True,
                'original_message_id': self.id,
            }
        }
    
    def action_forward(self):
        """Open forward composer using send mail wizard"""
        self.ensure_one()
        forward_body = self._get_forward_body()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Forward'),
            'res_model': 'gmail.send.mail',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_account_id': self.account_id.id,
                'default_subject': f'Fwd: {self.subject or ""}',
                'default_body_html': forward_body,
                'is_forward': True,
                'original_message_id': self.id,
            }
        }
    
    def action_view_attachments(self):
        """View message attachments"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attachments'),
            'res_model': 'gmail.attachment',
            'view_mode': 'tree,form',
            'domain': [('message_id', '=', self.id)],
            'context': {'default_message_id': self.id},
        }
    
    def _sync_read_status(self):
        """Sync read status with Gmail API"""
        self.ensure_one()
        # Gmail API implementation for updating read status
        try:
            _logger.info(f'Syncing read status for message {self.gmail_message_id}')
            # Implementation will be added when Gmail API is integrated
        except Exception as e:
            _logger.error(f'Failed to sync read status: {str(e)}')
    
    def _sync_star_status(self):
        """Sync star status with Gmail API"""
        self.ensure_one()
        # Gmail API implementation for updating star status
        try:
            _logger.info(f'Syncing star status for message {self.gmail_message_id}')
            # Implementation will be added when Gmail API is integrated
        except Exception as e:
            _logger.error(f'Failed to sync star status: {str(e)}')
    
    def _get_forward_body(self):
        """Get formatted body for forwarding"""
        self.ensure_one()
        body = f'<br/><br/>---------- Forwarded message ----------<br/>'
        body += f'<b>From:</b> {self.from_name or self.from_email}<br/>'
        body += f'<b>Date:</b> {self.date}<br/>'
        body += f'<b>Subject:</b> {self.subject or "(No Subject)"}<br/>'
        body += f'<b>To:</b> {self.to_emails}<br/>'
        if self.cc_emails:
            body += f'<b>CC:</b> {self.cc_emails}<br/>'
        body += f'<br/>{self.body_html or self.body_plain or ""}'
        return body
    
    @api.model
    def cleanup_old_messages(self, days=30):
        """Clean up old messages (called by cron)"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_messages = self.search([
            ('sync_date', '<', cutoff_date),
            ('is_starred', '=', False),
            ('is_important', '=', False),
        ])
        _logger.info(f'Cleaning up {len(old_messages)} old messages')
        old_messages.unlink()
