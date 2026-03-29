# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = 'mail.mail'

    # Add field to track if email was sent via Gmail
    sent_via_gmail = fields.Boolean(
        string='Sent via Gmail',
        default=False,
        help='Whether this email was sent through Gmail API'
    )
    gmail_account_used = fields.Many2one(
        'gmail.account',
        string='Gmail Account Used',
        help='Gmail account used to send this email'
    )

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        """Override mail sending to route through Gmail when configured"""
        
        # Check if Gmail integration is enabled for notifications
        gmail_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'gmail_integration.enable_notification_routing', False
        )
        
        if not gmail_enabled:
            # Use standard Odoo email sending
            return super()._send(auto_commit=auto_commit, raise_exception=raise_exception, smtp_session=smtp_session)
        
        # Get target Gmail account for notifications
        target_email = self.env['ir.config_parameter'].sudo().get_param(
            'gmail_integration.notification_target_email'
        )
        
        if not target_email:
            _logger.warning('Gmail notification routing enabled but no target email configured')
            return super()._send(auto_commit=auto_commit, raise_exception=raise_exception, smtp_session=smtp_session)
        
        # Find Gmail account to send from
        gmail_account = self._get_gmail_account_for_sending()
        
        if not gmail_account:
            _logger.warning('No connected Gmail account found for sending notifications')
            return super()._send(auto_commit=auto_commit, raise_exception=raise_exception, smtp_session=smtp_session)
        
        # Send emails through Gmail API
        gmail_sent_count = 0
        for mail in self:
            try:
                if mail._should_send_via_gmail():
                    mail._send_via_gmail_api(gmail_account, target_email)
                    gmail_sent_count += 1
                else:
                    # Use standard sending for this email
                    super(MailMail, mail)._send(auto_commit=auto_commit, raise_exception=raise_exception, smtp_session=smtp_session)
            except Exception as e:
                _logger.error(f'Failed to send email via Gmail: {str(e)}')
                if raise_exception:
                    raise
                # Fallback to standard sending
                super(MailMail, mail)._send(auto_commit=auto_commit, raise_exception=raise_exception, smtp_session=smtp_session)
        
        _logger.info(f'Sent {gmail_sent_count} emails via Gmail API')
        return True

    def _should_send_via_gmail(self):
        """Determine if this email should be sent via Gmail"""
        self.ensure_one()
        
        # Skip if already sent
        if self.state == 'sent':
            return False
        
        # Skip if not outgoing
        if self.state != 'outgoing':
            return False
        
        # Check if this is a system notification (from modules like fleet, hr, etc.)
        notification_types = [
            'fleet',      # Fleet module notifications
            'hr',         # HR module notifications  
            'project',    # Project notifications
            'crm',        # CRM notifications
            'sale',       # Sales notifications
            'purchase',   # Purchase notifications
            'account',    # Accounting notifications
            'stock',      # Inventory notifications
        ]
        
        # Check if email is from a module that should use Gmail
        model = self.model if self.model else ''
        for notification_type in notification_types:
            if notification_type in model.lower():
                return True
        
        # Check if email subject contains notification keywords
        subject = self.subject or ''
        notification_keywords = [
            'expir',         # License expiring, contract expiring
            'reminder',      # Reminders
            'alert',         # Alerts
            'notification',  # General notifications
            'warning',       # Warnings
            'overdue',       # Overdue items
            'deadline',      # Deadlines
            'maintenance',   # Maintenance reminders
            'renewal',       # Renewals
        ]
        
        for keyword in notification_keywords:
            if keyword in subject.lower():
                return True
        
        return False

    def _get_gmail_account_for_sending(self):
        """Get Gmail account to use for sending notifications"""
        
        # Try to get specifically configured notification account
        notification_account_id = self.env['ir.config_parameter'].sudo().get_param(
            'gmail_integration.notification_gmail_account_id'
        )
        
        if notification_account_id:
            account = self.env['gmail.account'].sudo().browse(int(notification_account_id))
            if account.exists() and account.status == 'connected':
                return account
        
        # Fallback to first connected Gmail account
        account = self.env['gmail.account'].sudo().search([
            ('status', '=', 'connected')
        ], limit=1)
        
        return account if account else None

    def _send_via_gmail_api(self, gmail_account, target_email):
        """Send email via Gmail API"""
        self.ensure_one()
        
        try:
            # Prepare email content for Gmail
            subject = self.subject or 'Odoo Notification'
            
            # Create comprehensive email body
            body_html = self._prepare_gmail_notification_body()
            body_plain = self._prepare_gmail_notification_plain_body()
            
            # Send via Gmail API
            gmail_message_id = gmail_account.send_email(
                to_emails=[target_email],
                subject=f'[Odoo] {subject}',
                body_html=body_html,
                body_plain=body_plain,
                cc_emails=None,
                bcc_emails=None,
                attachments=None
            )
            
            # Update mail record
            self.write({
                'state': 'sent',
                'sent_via_gmail': True,
                'gmail_account_used': gmail_account.id,
                'message_id': gmail_message_id,
            })
            
            # Create Gmail message record for tracking
            self._create_gmail_message_record(gmail_account, gmail_message_id, target_email)
            
            _logger.info(f'Email sent via Gmail API: {subject} to {target_email}')
            
        except Exception as e:
            _logger.error(f'Gmail API sending failed: {str(e)}')
            # Mark as exception for retry
            self.write({
                'state': 'exception',
                'failure_reason': str(e),
            })
            raise

    def _prepare_gmail_notification_body(self):
        """Prepare HTML email body for Gmail notification"""
        self.ensure_one()
        
        # Get original body
        original_body = self.body_html or self.body or ''
        
        # Add Odoo notification wrapper
        body_html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #875A7B; color: white; padding: 20px; text-align: center;">
                <h2 style="margin: 0;">Odoo Notification</h2>
                <p style="margin: 5px 0 0 0;">System Alert from {self.env.company.name}</p>
            </div>
            
            <div style="padding: 20px; border: 1px solid #ddd;">
                <h3 style="color: #875A7B; margin-top: 0;">
                    {self.subject or 'Notification'}
                </h3>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    {original_body}
                </div>
                
                <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee;">
                    <p style="margin: 0; color: #666; font-size: 12px;">
                        <strong>Source:</strong> {self.model or 'System'}<br/>
                        <strong>Time:</strong> {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
                        <strong>Database:</strong> {self.env.cr.dbname}
                    </p>
                </div>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666;">
                This is an automated notification from your Odoo system.
            </div>
        </div>
        '''
        
        return body_html

    def _prepare_gmail_notification_plain_body(self):
        """Prepare plain text email body for Gmail notification"""
        self.ensure_one()
        
        # Get original body (strip HTML if needed)
        import re
        original_body = self.body_html or self.body or ''
        # Simple HTML tag removal
        plain_body = re.sub(r'<[^>]+>', '', original_body)
        
        body_plain = f'''
ODOO NOTIFICATION
================

Subject: {self.subject or 'Notification'}
From: {self.env.company.name}

{plain_body}

---
Source: {self.model or 'System'}
Time: {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Database: {self.env.cr.dbname}

This is an automated notification from your Odoo system.
        '''
        
        return body_plain

    def _create_gmail_message_record(self, gmail_account, gmail_message_id, target_email):
        """Create Gmail message record for sent notification"""
        self.ensure_one()
        
        try:
            # Create Gmail message record
            message_vals = {
                'gmail_message_id': gmail_message_id,
                'account_id': gmail_account.id,
                'subject': f'[Odoo] {self.subject}',
                'body_html': self._prepare_gmail_notification_body(),
                'body_plain': self._prepare_gmail_notification_plain_body(),
                'from_email': gmail_account.email_address,
                'from_name': f'{self.env.company.name} (Odoo)',
                'to_emails': target_email,
                'date': fields.Datetime.now(),
                'direction': 'outbound',
                'is_read': True,  # Sent emails are considered "read"
                'sync_status': 'synced',
                'sync_date': fields.Datetime.now(),
            }
            
            self.env['gmail.message'].sudo().create(message_vals)
            
        except Exception as e:
            _logger.warning(f'Failed to create Gmail message record: {str(e)}')
            # Don't fail the email sending for this


class GmailNotificationSettings(models.TransientModel):
    _name = 'gmail.notification.settings'
    _description = 'Gmail Notification Settings'

    enable_notification_routing = fields.Boolean(
        string='Enable Gmail Notification Routing',
        default=False,
        help='Route Odoo system notifications through Gmail API'
    )
    
    notification_target_email = fields.Char(
        string='Target Email Address',
        help='Email address to receive all Odoo notifications'
    )
    
    notification_gmail_account_id = fields.Many2one(
        'gmail.account',
        string='Gmail Account for Sending',
        domain=[('status', '=', 'connected')],
        help='Gmail account to use for sending notifications'
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        
        res.update(
            enable_notification_routing=params.get_param('gmail_integration.enable_notification_routing', False),
            notification_target_email=params.get_param('gmail_integration.notification_target_email', ''),
            notification_gmail_account_id=int(params.get_param('gmail_integration.notification_gmail_account_id', 0)) or False,
        )
        return res

    def set_values(self):
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        
        params.set_param('gmail_integration.enable_notification_routing', self.enable_notification_routing)
        params.set_param('gmail_integration.notification_target_email', self.notification_target_email or '')
        params.set_param('gmail_integration.notification_gmail_account_id', self.notification_gmail_account_id.id or 0)

    def action_test_notification(self):
        """Send a test notification"""
        self.ensure_one()
        
        if not self.enable_notification_routing:
            raise UserError(_('Gmail notification routing is not enabled'))
        
        if not self.notification_target_email:
            raise UserError(_('Target email address is not configured'))
        
        if not self.notification_gmail_account_id:
            raise UserError(_('Gmail account for sending is not configured'))
        
        # Create a test email
        test_mail = self.env['mail.mail'].create({
            'subject': 'Test Notification from Odoo',
            'body_html': '<p>This is a test notification to verify Gmail integration is working correctly.</p>',
            'email_to': self.notification_target_email,
            'model': 'gmail.notification.test',
            'state': 'outgoing',
        })
        
        # Send it
        test_mail._send()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test Notification Sent'),
                'message': _('Test notification has been sent to %s') % self.notification_target_email,
                'type': 'success',
            }
        }
