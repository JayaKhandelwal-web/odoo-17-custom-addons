# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class GmailThread(models.Model):
    _name = 'gmail.thread'
    _description = 'Gmail Thread (Conversation)'
    _rec_name = 'subject'
    _order = 'last_activity_date desc, id desc'

    # Gmail Thread Identifier
    gmail_thread_id = fields.Char(
        string='Gmail Thread ID',
        required=True,
        index=True,
        help='Unique Gmail thread identifier'
    )
    
    # Account Reference
    account_id = fields.Many2one(
        'gmail.account',
        string='Gmail Account',
        required=True,
        ondelete='cascade',
        help='Associated Gmail account'
    )
    
    # Thread Information
    subject = fields.Char(
        string='Subject',
        help='Thread subject (from first message)'
    )
    snippet = fields.Text(
        string='Snippet',
        help='Latest message snippet'
    )
    
    # Participants
    participants = fields.Text(
        string='Participants',
        help='All email addresses in this thread (comma separated)'
    )
    participant_names = fields.Text(
        string='Participant Names',
        help='All participant names in this thread'
    )
    
    # Thread Metadata
    message_count = fields.Integer(
        string='Message Count',
        compute='_compute_thread_stats',
        store=True,
        help='Number of messages in thread'
    )
    unread_count = fields.Integer(
        string='Unread Count',
        compute='_compute_thread_stats',
        store=True,
        help='Number of unread messages in thread'
    )
    attachment_count = fields.Integer(
        string='Attachment Count',
        compute='_compute_thread_stats',
        store=True,
        help='Total attachments in thread'
    )
    
    # Thread Status
    is_read = fields.Boolean(
        string='All Read',
        compute='_compute_thread_status',
        help='Whether all messages in thread are read'
    )
    is_starred = fields.Boolean(
        string='Has Starred',
        compute='_compute_thread_status',
        help='Whether thread contains starred messages'
    )
    is_important = fields.Boolean(
        string='Important',
        compute='_compute_thread_status',
        help='Whether thread contains important messages'
    )
    has_attachments = fields.Boolean(
        string='Has Attachments',
        compute='_compute_thread_status',
        help='Whether thread contains attachments'
    )
    
    # Dates
    first_message_date = fields.Datetime(
        string='First Message Date',
        compute='_compute_thread_dates',
        store=True,
        help='Date of first message in thread'
    )
    last_message_date = fields.Datetime(
        string='Last Message Date',
        compute='_compute_thread_dates',
        store=True,
        help='Date of latest message in thread'
    )
    last_activity_date = fields.Datetime(
        string='Last Activity',
        compute='_compute_thread_dates',
        store=True,
        help='Date of last activity in thread'
    )
    
    # Gmail Labels
    gmail_labels = fields.Text(
        string='Gmail Labels',
        help='Gmail labels applied to thread'
    )
    
    # Thread State
    state = fields.Selection([
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('spam', 'Spam'),
        ('trash', 'Trash'),
    ], string='State', default='active',
       help='Thread state in Gmail')
    
    # Relations
    message_ids = fields.One2many(
        'gmail.message',
        'thread_id',
        string='Messages',
        help='Messages in this thread'
    )
    
    # Partner Relations
    partner_ids = fields.Many2many(
        'res.partner',
        'gmail_thread_partner_rel',
        'thread_id',
        'partner_id',
        string='Partners',
        help='Partners involved in this thread'
    )
    
    # Constraints
    _sql_constraints = [
        ('unique_gmail_thread', 'unique(gmail_thread_id, account_id)', 
         'Gmail thread ID must be unique per account!'),
    ]
    
    @api.depends('message_ids', 'message_ids.is_read', 'message_ids.attachment_ids')
    def _compute_thread_stats(self):
        for record in self:
            messages = record.message_ids
            record.message_count = len(messages)
            record.unread_count = len(messages.filtered(lambda m: not m.is_read))
            
            attachment_count = 0
            for message in messages:
                attachment_count += len(message.attachment_ids)
            record.attachment_count = attachment_count
    
    @api.depends('message_ids', 'message_ids.is_read', 'message_ids.is_starred', 
                 'message_ids.is_important', 'message_ids.attachment_ids')
    def _compute_thread_status(self):
        for record in self:
            messages = record.message_ids
            
            # Check if all messages are read
            record.is_read = all(msg.is_read for msg in messages) if messages else True
            
            # Check if any message is starred
            record.is_starred = any(msg.is_starred for msg in messages)
            
            # Check if any message is important
            record.is_important = any(msg.is_important for msg in messages)
            
            # Check if thread has attachments
            record.has_attachments = any(msg.attachment_ids for msg in messages)
    
    @api.depends('message_ids', 'message_ids.date', 'message_ids.last_updated')
    def _compute_thread_dates(self):
        for record in self:
            messages = record.message_ids.sorted('date')
            if messages:
                record.first_message_date = messages[0].date
                record.last_message_date = messages[-1].date
                
                # Last activity is the most recent between message date and last update
                last_activity = max([msg.last_updated or msg.date for msg in messages])
                record.last_activity_date = last_activity
            else:
                record.first_message_date = False
                record.last_message_date = False
                record.last_activity_date = False
    
    @api.model_create_multi
    def create(self, vals_list):
        threads = super().create(vals_list)
        
        # Update participants and partner relations after creation
        for thread in threads:
            thread._update_participants()
            thread._update_partners()
        
        return threads
    
    def write(self, vals):
        result = super().write(vals)
        
        # Update participants when messages change
        if 'message_ids' in vals:
            for record in self:
                record._update_participants()
                record._update_partners()
        
        return result
    
    def _update_participants(self):
        """Update participant list from messages"""
        self.ensure_one()
        
        participants = set()
        participant_names = set()
        
        for message in self.message_ids:
            # Add sender
            if message.from_email:
                participants.add(message.from_email)
            if message.from_name:
                participant_names.add(message.from_name)
            
            # Add recipients
            for email_field in ['to_emails', 'cc_emails', 'bcc_emails']:
                emails = getattr(message, email_field)
                if emails:
                    for email in emails.split(','):
                        email = email.strip()
                        if email:
                            participants.add(email)
        
        self.participants = ', '.join(sorted(participants))
        self.participant_names = ', '.join(sorted(participant_names)) if participant_names else ''
    
    def _update_partners(self):
        """Update partner relations from participants"""
        self.ensure_one()
        
        if not self.participants:
            return
        
        partner_ids = []
        emails = [email.strip() for email in self.participants.split(',') if email.strip()]
        
        for email in emails:
            partner = self.env['res.partner'].search([('email', '=', email)], limit=1)
            if partner:
                partner_ids.append(partner.id)
        
        if partner_ids:
            self.partner_ids = [(6, 0, partner_ids)]
    
    def action_mark_read(self):
        """Mark all messages in thread as read"""
        self.ensure_one()
        unread_messages = self.message_ids.filtered(lambda m: not m.is_read)
        if unread_messages:
            unread_messages.write({'is_read': True})
            # Sync with Gmail API
            for message in unread_messages:
                message._sync_read_status()
    
    def action_mark_unread(self):
        """Mark all messages in thread as unread"""
        self.ensure_one()
        read_messages = self.message_ids.filtered(lambda m: m.is_read)
        if read_messages:
            read_messages.write({'is_read': False})
            # Sync with Gmail API
            for message in read_messages:
                message._sync_read_status()
    
    def action_archive(self):
        """Archive thread"""
        self.ensure_one()
        self.state = 'archived'
        # Sync with Gmail API
        self._sync_thread_state()
    
    def action_unarchive(self):
        """Unarchive thread"""
        self.ensure_one()
        self.state = 'active'
        # Sync with Gmail API
        self._sync_thread_state()
    
    def action_delete(self):
        """Move thread to trash"""
        self.ensure_one()
        self.state = 'trash'
        # Sync with Gmail API
        self._sync_thread_state()
    
    def action_reply(self):
        """Reply to thread"""
        self.ensure_one()
        latest_message = self.message_ids.sorted('date', reverse=True)[0] if self.message_ids else False
        
        if not latest_message:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reply to Thread'),
            'res_model': 'gmail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_thread_id': self.id,
                'default_original_message_id': latest_message.id,
                'default_reply_to': latest_message.from_email,
                'default_subject': f'Re: {self.subject or ""}',
                'default_account_id': self.account_id.id,
            }
        }
    
    def action_view_messages(self):
        """View all messages in thread"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Thread Messages'),
            'res_model': 'gmail.message',
            'view_mode': 'tree,form',
            'domain': [('thread_id', '=', self.id)],
            'context': {
                'default_thread_id': self.id,
                'default_account_id': self.account_id.id,
            }
        }
    
    def _sync_thread_state(self):
        """Sync thread state with Gmail API"""
        self.ensure_one()
        try:
            _logger.info(f'Syncing thread state for {self.gmail_thread_id}')
            # Gmail API implementation for updating thread state
            # Implementation will be added when Gmail API is integrated
        except Exception as e:
            _logger.error(f'Failed to sync thread state: {str(e)}')
    
    @api.model
    def create_or_update_from_gmail(self, gmail_thread_data, account_id):
        """Create or update thread from Gmail API data"""
        gmail_thread_id = gmail_thread_data.get('id')
        
        existing_thread = self.search([
            ('gmail_thread_id', '=', gmail_thread_id),
            ('account_id', '=', account_id)
        ], limit=1)
        
        thread_vals = {
            'gmail_thread_id': gmail_thread_id,
            'account_id': account_id,
            'gmail_labels': str(gmail_thread_data.get('labels', [])),
        }
        
        # Extract subject from first message if available
        messages = gmail_thread_data.get('messages', [])
        if messages:
            first_message = messages[0]
            headers = {h['name']: h['value'] for h in first_message.get('payload', {}).get('headers', [])}
            thread_vals['subject'] = headers.get('Subject', '')
        
        if existing_thread:
            existing_thread.write(thread_vals)
            return existing_thread
        else:
            return self.create(thread_vals)
