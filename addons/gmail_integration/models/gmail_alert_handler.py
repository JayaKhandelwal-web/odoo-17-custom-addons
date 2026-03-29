# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import json
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class GmailAlertHandler(models.Model):
    """
    Enhanced Gmail Alert Handler with Template Mapping Support
    
    Handles alerts from ANY module using dynamic template mappings
    Supports Fleet, Inventory, HR, and any other module alerts
    """
    _name = 'gmail.alert.handler'
    _description = 'Gmail Alert Handler'
    _rec_name = 'name'
    _order = 'alert_date desc'

    # Alert Identification
    name = fields.Char(
        string='Alert Name',
        required=True,
        help='Human-readable name for this alert'
    )

    alert_type = fields.Char(
        string='Alert Type',
        required=True,
        help='Type of alert (e.g., document_expiry, low_stock, work_order)'
    )

    alert_level = fields.Char(
        string='Alert Level',
        help='Alert level/severity (e.g., 30_days, critical, overdue)'
    )

    source_module = fields.Char(
        string='Source Module',
        required=True,
        help='Module that generated this alert'
    )

    # Alert Data
    alert_data = fields.Text(
        string='Alert Data',
        help='JSON data containing alert specifics'
    )

    alert_date = fields.Datetime(
        string='Alert Date',
        default=fields.Datetime.now,
        required=True,
        help='When the alert was generated'
    )

    # Email Information
    sent_from_account = fields.Many2one(
        'gmail.account',
        string='Sent From Account',
        help='Gmail account used to send this alert'
    )

    template_used = fields.Many2one(
        'gmail.template',
        string='Template Used',
        help='Email template used for this alert'
    )

    email_subject = fields.Char(
        string='Email Subject',
        help='Subject line of the sent email'
    )

    recipients = fields.Text(
        string='Recipients',
        help='Email addresses that received this alert'
    )

    # Status Information
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('ignored', 'Ignored'),
    ], string='Status',
       default='pending',
       required=True)

    sent_date = fields.Datetime(
        string='Sent Date',
        help='When the email was actually sent'
    )

    error_message = fields.Text(
        string='Error Message',
        help='Error details if sending failed'
    )

    # Tracking
    retry_count = fields.Integer(
        string='Retry Count',
        default=0,
        help='Number of times sending was attempted'
    )

    # ============================================
    # MAIN ALERT SENDING METHOD
    # ============================================

    @api.model
    def send_alert(self, alert_type, alert_data, source_module, alert_level=None, 
                   recipients=None, force_send=False, **kwargs):
        """
        Enhanced Send Alert with Template Mapping Support
        
        Args:
            alert_type (str): Type of alert (document_expiry, low_stock, etc.)
            alert_data (dict): Data for the alert
            source_module (str): Module generating the alert  
            alert_level (str): Alert level (30_days, critical, etc.)
            recipients (list): Additional recipients
            force_send (bool): Skip duplicate prevention
            **kwargs: Additional parameters
            
        Returns:
            dict: Result with success status and message
        """
        try:
            # Check if alert system is enabled
            if not self._is_alert_system_enabled():
                return {
                    'success': False,
                    'message': 'Alert system is disabled'
                }

            # Check for duplicates (unless forced)
            if not force_send and self._should_prevent_duplicate(alert_type, alert_level, alert_data):
                return {
                    'success': False,
                    'message': 'Duplicate alert prevented'
                }

            # Get alert configuration
            config = self.env['gmail.alert.settings'].get_active_config()

            # Generate alert name
            alert_name = self._generate_alert_name(source_module, alert_type, alert_level, alert_data)

            # Create alert record
            alert_record = self.create({
                'name': alert_name,
                'alert_type': alert_type,
                'alert_level': alert_level,
                'source_module': source_module,
                'alert_data': json.dumps(alert_data) if isinstance(alert_data, dict) else str(alert_data),
                'status': 'pending'
            })

            # Get template using new mapping system
            template = self._get_template_for_alert(config, source_module, alert_type, alert_level)
            
            if not template:
                alert_record.write({
                    'status': 'failed',
                    'error_message': f'No template found for {source_module} → {alert_type} → {alert_level}'
                })
                return {
                    'success': False,
                    'message': f'No template found for {source_module} → {alert_type} → {alert_level}'
                }

            # Get Gmail account
            gmail_account = config.default_account_id
            if not gmail_account or gmail_account.status != 'connected':
                alert_record.write({
                    'status': 'failed',
                    'error_message': 'No connected Gmail account available'
                })
                return {
                    'success': False,
                    'message': 'No connected Gmail account available'
                }

            # Prepare recipients
            all_recipients = self._prepare_recipients(config, recipients)
            if not all_recipients:
                alert_record.write({
                    'status': 'failed',
                    'error_message': 'No recipients configured'
                })
                return {
                    'success': False,
                    'message': 'No recipients configured'
                }

            # Prepare email data
            email_data = self._prepare_email_data(alert_data, source_module, alert_type, alert_level)

            # Send email using template
            send_result = self._send_email_with_template(
                template, gmail_account, all_recipients, email_data, alert_record
            )

            # Update alert record
            if send_result['success']:
                alert_record.write({
                    'status': 'sent',
                    'sent_date': fields.Datetime.now(),
                    'sent_from_account': gmail_account.id,
                    'template_used': template.id,
                    'email_subject': send_result.get('subject', ''),
                    'recipients': ', '.join(all_recipients)
                })
                
                return {
                    'success': True,
                    'message': f'Alert sent successfully to {len(all_recipients)} recipients',
                    'alert_id': alert_record.id
                }
            else:
                alert_record.write({
                    'status': 'failed',
                    'error_message': send_result.get('error', 'Unknown error'),
                    'retry_count': alert_record.retry_count + 1
                })
                
                return {
                    'success': False,
                    'message': send_result.get('error', 'Unknown error'),
                    'alert_id': alert_record.id
                }

        except Exception as e:
            _logger.error(f'Error sending alert: {str(e)}')
            return {
                'success': False,
                'message': f'Exception: {str(e)}'
            }

    # ============================================
    # TEMPLATE RESOLUTION METHODS
    # ============================================

    def _get_template_for_alert(self, config, source_module, alert_type, alert_level=None):
        """Get template using new mapping system or fallback methods"""
        
        # Method 1: Use Template Mappings (Preferred)
        if config.template_search_strategy == 'mapping':
            template = config.get_template_for_alert(source_module, alert_type, alert_level)
            if template:
                _logger.info(f'Found template via mapping: {template.name}')
                return template

        # Method 2: Exact name matching (Legacy support)
        if config.template_search_strategy in ['exact', 'fallback', 'fuzzy']:
            template = self._find_template_by_naming_convention(source_module, alert_type, alert_level)
            if template:
                _logger.info(f'Found template via naming convention: {template.name}')
                return template

        # Method 3: Fallback to default template
        if config.default_template_id:
            _logger.info(f'Using fallback template: {config.default_template_id.name}')
            return config.default_template_id

        # No template found
        _logger.warning(f'No template found for {source_module} → {alert_type} → {alert_level}')
        return None

    def _find_template_by_naming_convention(self, source_module, alert_type, alert_level=None):
        """Find template using naming convention (legacy support)"""
        GmailTemplate = self.env['gmail.template']
        
        # Try exact match first
        if alert_level:
            exact_name = f"{source_module}_{alert_type}_{alert_level}"
            template = GmailTemplate.search([('name', 'ilike', exact_name)], limit=1)
            if template:
                return template
        
        # Try without level
        general_name = f"{source_module}_{alert_type}"
        template = GmailTemplate.search([('name', 'ilike', general_name)], limit=1)
        if template:
            return template
            
        return None

    # ============================================
    # EMAIL PREPARATION METHODS
    # ============================================

    def _prepare_recipients(self, config, additional_recipients=None):
        """Prepare complete recipient list"""
        recipients = []
        
        # Add global recipients
        global_recipients = config.get_global_recipients()
        recipients.extend(global_recipients)
        
        # Add additional recipients
        if additional_recipients:
            if isinstance(additional_recipients, str):
                additional_recipients = [email.strip() for email in additional_recipients.split(',')]
            recipients.extend(additional_recipients)
        
        # Remove duplicates and empty entries
        recipients = list(set([email.strip() for email in recipients if email.strip()]))
        
        return recipients

    def _prepare_email_data(self, alert_data, source_module, alert_type, alert_level):
        """Prepare email template data"""
        email_data = {}
        
        # Add alert_data if it's a dict
        if isinstance(alert_data, dict):
            email_data.update(alert_data)
        
        # Add standard alert information
        email_data.update({
            'alert_type': alert_type,
            'alert_level': alert_level,
            'source_module': source_module,
            'alert_date': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'company_name': self.env.company.name,
            'current_user': self.env.user.name,
        })
        
        return email_data

    def _send_email_with_template(self, template, gmail_account, recipients, email_data, alert_record):
        """Send email using template"""
        try:
            # Prepare template context
            template_context = {
                'object': alert_record,
                'ctx': self.env.context,
            }
            template_context.update(email_data)
            
            # Render subject and body
            subject = template.subject or 'Alert Notification'
            body = template.body_html or template.body_text or 'Alert notification'
            
            # Simple template variable replacement
            for key, value in email_data.items():
                placeholder = f'{{{{{key}}}}}'
                subject = subject.replace(placeholder, str(value))
                body = body.replace(placeholder, str(value))
            
            # Send email through Gmail account
            result = gmail_account.send_email(
                recipients=recipients,
                subject=subject,
                body=body,
                body_type='html' if template.body_html else 'text'
            )
            
            return {
                'success': result.get('success', False),
                'subject': subject,
                'error': result.get('error', '') if not result.get('success') else None
            }
            
        except Exception as e:
            _logger.error(f'Error sending email with template: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }

    # ============================================
    # UTILITY METHODS
    # ============================================

    def _is_alert_system_enabled(self):
        """Check if alert system is enabled"""
        return self.env['gmail.alert.settings'].is_alert_system_enabled()

    def _should_prevent_duplicate(self, alert_type, alert_level, alert_data):
        """Check if duplicate should be prevented"""
        config = self.env['gmail.alert.settings'].get_active_config()
        
        if not config.duplicate_prevention:
            return False
        
        # Check for recent similar alerts
        prevention_hours = config.get_duplicate_prevention_hours()
        cutoff_time = datetime.now() - timedelta(hours=prevention_hours)
        
        # Create a simple hash of alert data for comparison
        alert_hash = str(hash(f"{alert_type}_{alert_level}_{str(alert_data)}"))
        
        similar_alerts = self.search([
            ('alert_type', '=', alert_type),
            ('alert_level', '=', alert_level),
            ('alert_date', '>=', cutoff_time),
            ('status', '=', 'sent')
        ])
        
        # Simple duplicate check - could be enhanced
        return len(similar_alerts) > 0

    def _generate_alert_name(self, source_module, alert_type, alert_level, alert_data):
        """Generate human-readable alert name"""
        parts = [source_module.title(), alert_type.replace('_', ' ').title()]
        
        if alert_level:
            parts.append(alert_level.replace('_', ' ').title())
        
        # Add specific data if available
        if isinstance(alert_data, dict):
            if 'document_name' in alert_data:
                parts.append(f"({alert_data['document_name']})")
            elif 'vehicle_name' in alert_data:
                parts.append(f"({alert_data['vehicle_name']})")
            elif 'product_name' in alert_data:
                parts.append(f"({alert_data['product_name']})")
        
        return ' - '.join(parts)

    # ============================================
    # ACTION METHODS
    # ============================================

    def action_resend_alert(self):
        """Resend failed alert"""
        self.ensure_one()
        
        if self.status not in ['failed', 'pending']:
            raise UserError(_('Can only resend failed or pending alerts'))
        
        try:
            # Parse alert data
            alert_data = json.loads(self.alert_data) if self.alert_data else {}
            
            # Resend the alert
            result = self.send_alert(
                alert_type=self.alert_type,
                alert_level=self.alert_level,
                alert_data=alert_data,
                source_module=self.source_module,
                force_send=True
            )
            
            if result['success']:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Alert Resent'),
                        'message': _('Alert was resent successfully!'),
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Resend Failed'),
                        'message': _('Failed to resend: %s') % result['message'],
                        'type': 'danger',
                    }
                }
                
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Resend Error'),
                    'message': _('Error: %s') % str(e),
                    'type': 'danger',
                }
            }

    # ============================================
    # CLEANUP METHODS
    # ============================================

    @api.model
    def cleanup_old_alerts(self, days=30):
        """Cleanup old alert records"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        old_alerts = self.search([
            ('alert_date', '<', cutoff_date),
            ('status', 'in', ['sent', 'failed', 'ignored'])
        ])
        
        count = len(old_alerts)
        old_alerts.unlink()
        
        _logger.info(f'Cleaned up {count} old alert records older than {days} days')
        return count

    @api.model
    def auto_cleanup_cron(self):
        """Cron job for automatic cleanup"""
        config = self.env['gmail.alert.settings'].get_active_config()
        
        if config.auto_cleanup_enabled:
            self.cleanup_old_alerts(config.cleanup_after_days)

    # ============================================
    # REPORTING METHODS
    # ============================================

    @api.model
    def get_alert_statistics(self, days=7):
        """Get alert statistics for reporting"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        stats = {
            'total_alerts': self.search_count([('alert_date', '>=', cutoff_date)]),
            'sent_alerts': self.search_count([('alert_date', '>=', cutoff_date), ('status', '=', 'sent')]),
            'failed_alerts': self.search_count([('alert_date', '>=', cutoff_date), ('status', '=', 'failed')]),
            'pending_alerts': self.search_count([('alert_date', '>=', cutoff_date), ('status', '=', 'pending')]),
        }
        
        stats['success_rate'] = (stats['sent_alerts'] / stats['total_alerts'] * 100) if stats['total_alerts'] > 0 else 0
        
        return stats

    @api.model
    def generate_daily_summary(self):
        """Generate daily alert summary"""
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        alerts_today = self.search([('alert_date', '>=', today_start)])
        
        summary = {
            'date': today.strftime('%Y-%m-%d'),
            'total_alerts': len(alerts_today),
            'sent': len(alerts_today.filtered(lambda a: a.status == 'sent')),
            'failed': len(alerts_today.filtered(lambda a: a.status == 'failed')),
            'pending': len(alerts_today.filtered(lambda a: a.status == 'pending')),
            'by_module': {},
            'by_type': {}
        }
        
        # Group by module
        for alert in alerts_today:
            module = alert.source_module
            if module not in summary['by_module']:
                summary['by_module'][module] = 0
            summary['by_module'][module] += 1
        
        # Group by type
        for alert in alerts_today:
            alert_type = alert.alert_type
            if alert_type not in summary['by_type']:
                summary['by_type'][alert_type] = 0
            summary['by_type'][alert_type] += 1
        
        return summary