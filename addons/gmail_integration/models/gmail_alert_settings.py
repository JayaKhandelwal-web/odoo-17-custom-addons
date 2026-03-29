# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re
import logging
import json

_logger = logging.getLogger(__name__)


class GmailAlertSettings(models.Model):
    """
    Generic Alert System Configuration
    
    Supports alerts from ANY module (Fleet, Inventory, HR, etc.)
    Dynamic template mapping for scalable alert types
    """
    _name = 'gmail.alert.settings'
    _description = 'Gmail Alert System Configuration'
    _rec_name = 'name'
    _order = 'id desc'

    # Basic Information
    name = fields.Char(
        string='Configuration Name',
        default='Alert System Configuration',
        required=True,
        help='Name for this alert configuration'
    )

    # ============================================
    # MAIN ALERT SYSTEM SETTINGS
    # ============================================

    # System Enable/Disable
    system_enabled = fields.Boolean(
        string='Enable Alert System',
        default=True,
        help='Master switch - enable/disable entire alert system'
    )

    # Default Gmail Account
    default_account_id = fields.Many2one(
        'gmail.account',
        string='Default Alert Account',
        domain="[('status', '=', 'connected')]",
        help='Default Gmail account for sending alerts from any module'
    )

    # Fixed Recipients (Global)
    global_recipients = fields.Text(
        string='Global Recipients',
        help='Email addresses to include in ALL alerts (comma-separated)\nExample: admin@company.com, alerts@company.com'
    )

    # ============================================
    # DYNAMIC TEMPLATE MAPPING
    # ============================================

    # Template Mappings (One2many)
    template_mapping_ids = fields.One2many(
        'gmail.alert.template.mapping',
        'settings_id',
        string='Template Mappings',
        help='Configure templates for different alert types'
    )

    # Template Mapping JSON (for quick lookup)
    template_mapping_json = fields.Text(
        string='Template Mapping JSON',
        compute='_compute_template_mapping_json',
        store=True,
        help='JSON representation of template mappings for quick lookup'
    )

    # ============================================
    # ALERT PROCESSING SETTINGS
    # ============================================

    # Duplicate Prevention
    duplicate_prevention = fields.Boolean(
        string='Prevent Duplicate Alerts',
        default=True,
        help='Prevent sending same alert multiple times within prevention window'
    )

    duplicate_prevention_hours = fields.Integer(
        string='Prevention Window (hours)',
        default=24,
        help='Hours to wait before allowing duplicate alert'
    )

    # Batch Processing
    batch_processing = fields.Boolean(
        string='Batch Processing',
        default=False,
        help='Process alerts in batches instead of immediately'
    )

    batch_interval_minutes = fields.Integer(
        string='Batch Interval (minutes)',
        default=60,
        help='How often to process batched alerts'
    )

    # ============================================
    # TEMPLATE SELECTION SETTINGS
    # ============================================

    # Template Search Strategy
    template_search_strategy = fields.Selection([
        ('mapping', 'Use Template Mappings'),
        ('exact', 'Exact Match Only'),
        ('fallback', 'Exact Match with Fallback'),
        ('fuzzy', 'Fuzzy Matching'),
    ], string='Template Search Strategy',
       default='mapping',
       help='How to find templates for alerts')

    # Default Template (Fallback)
    default_template_id = fields.Many2one(
        'gmail.template',
        string='Default Template',
        help='Fallback template when specific template not found'
    )

    # ============================================
    # ALERT CLEANUP SETTINGS
    # ============================================

    # Auto Cleanup
    auto_cleanup_enabled = fields.Boolean(
        string='Auto Cleanup Old Alerts',
        default=True,
        help='Automatically remove old alert records'
    )

    cleanup_after_days = fields.Integer(
        string='Keep Alerts (days)',
        default=30,
        help='Number of days to keep alert records'
    )

    # ============================================
    # NOTIFICATION SETTINGS
    # ============================================

    # Admin Notifications
    notify_admin_on_failure = fields.Boolean(
        string='Notify Admin on Failures',
        default=True,
        help='Send notification to admin when alert sending fails'
    )

    admin_notification_email = fields.Char(
        string='Admin Email',
        help='Email address for admin notifications'
    )

    # Daily Summary
    daily_summary_enabled = fields.Boolean(
        string='Daily Alert Summary',
        default=False,
        help='Send daily summary of all alerts sent'
    )

    summary_recipients = fields.Text(
        string='Summary Recipients',
        help='Recipients for daily alert summary (comma-separated)'
    )

    # ============================================
    # STATUS AND STATISTICS
    # ============================================

    # Configuration Status
    is_active = fields.Boolean(
        string='Active Configuration',
        default=True,
        help='Only one configuration can be active at a time'
    )

    config_status = fields.Selection([
        ('not_configured', 'Not Configured'),
        ('configured', 'Configured'),
        ('partial', 'Partially Configured'),
        ('error', 'Configuration Error'),
    ], string='Status',
       compute='_compute_config_status',
       store=True)

    # Statistics
    total_alerts_sent = fields.Integer(
        string='Total Alerts Sent',
        compute='_compute_statistics',
        help='Total number of alerts sent through this system'
    )

    alerts_today = fields.Integer(
        string='Alerts Today',
        compute='_compute_statistics',
        help='Number of alerts sent today'
    )

    failed_alerts = fields.Integer(
        string='Failed Alerts',
        compute='_compute_statistics',
        help='Number of failed alerts'
    )

    last_alert_date = fields.Datetime(
        string='Last Alert',
        compute='_compute_statistics',
        help='When the last alert was sent'
    )

    # System Info
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )

    last_test_date = fields.Datetime(
        string='Last Test Date',
        readonly=True
    )

    last_test_result = fields.Text(
        string='Last Test Result',
        readonly=True
    )

    # ============================================
    # COMPUTED FIELDS
    # ============================================

    @api.depends('template_mapping_ids', 'template_mapping_ids.module_name', 
                 'template_mapping_ids.alert_type', 'template_mapping_ids.alert_level',
                 'template_mapping_ids.template_id')
    def _compute_template_mapping_json(self):
        """Compute JSON representation of template mappings"""
        for record in self:
            mapping_dict = {}
            for mapping in record.template_mapping_ids:
                if mapping.template_id:
                    key = f"{mapping.module_name}_{mapping.alert_type}_{mapping.alert_level}"
                    mapping_dict[key] = {
                        'template_id': mapping.template_id.id,
                        'template_name': mapping.template_id.name,
                        'enabled': mapping.enabled
                    }
            record.template_mapping_json = json.dumps(mapping_dict)

    @api.depends('system_enabled', 'default_account_id', 'global_recipients')
    def _compute_config_status(self):
        """Compute configuration status"""
        for record in self:
            if not record.system_enabled:
                record.config_status = 'not_configured'
            elif not record.default_account_id:
                record.config_status = 'partial'
            elif record.default_account_id.status != 'connected':
                record.config_status = 'error'
            else:
                record.config_status = 'configured'

    @api.depends()
    def _compute_statistics(self):
        """Compute alert statistics"""
        for record in self:
            try:
                AlertHandler = self.env['gmail.alert.handler']

                # Total alerts
                record.total_alerts_sent = AlertHandler.search_count([
                    ('status', '=', 'sent')
                ])

                # Today's alerts
                today_start = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                record.alerts_today = AlertHandler.search_count([
                    ('status', '=', 'sent'),
                    ('sent_date', '>=', today_start)
                ])

                # Failed alerts
                record.failed_alerts = AlertHandler.search_count([
                    ('status', '=', 'failed')
                ])

                # Last alert date
                last_alert = AlertHandler.search([
                    ('status', '=', 'sent')
                ], order='sent_date desc', limit=1)

                record.last_alert_date = last_alert.sent_date if last_alert else False

            except Exception as e:
                _logger.warning(f'Error computing alert statistics: {e}')
                record.total_alerts_sent = 0
                record.alerts_today = 0
                record.failed_alerts = 0
                record.last_alert_date = False

    # ============================================
    # TEMPLATE MAPPING METHODS
    # ============================================

    def get_template_for_alert(self, module_name, alert_type, alert_level=None):
        """Get template for specific alert"""
        self.ensure_one()
        
        # Try exact match first
        if alert_level:
            key = f"{module_name}_{alert_type}_{alert_level}"
            mapping = self.template_mapping_ids.filtered(
                lambda m: m.module_name == module_name and 
                         m.alert_type == alert_type and 
                         m.alert_level == alert_level and
                         m.enabled and m.template_id
            )
            if mapping:
                return mapping[0].template_id
        
        # Try without level
        mapping = self.template_mapping_ids.filtered(
            lambda m: m.module_name == module_name and 
                     m.alert_type == alert_type and 
                     not m.alert_level and
                     m.enabled and m.template_id
        )
        if mapping:
            return mapping[0].template_id
            
        # Fallback to default template
        return self.default_template_id

    def action_auto_discover_templates(self):
        """Auto-discover and create template mappings"""
        self.ensure_one()
        
        # Get all available templates
        templates = self.env['gmail.template'].search([])
        
        # Common alert patterns to recognize
        alert_patterns = [
            # Fleet patterns
            ('fleet', 'document_expiry', '30_days'),
            ('fleet', 'document_expiry', '15_days'),
            ('fleet', 'document_expiry', '7_days'),
            ('fleet', 'document_expiry', 'expired'),
            ('fleet', 'work_order', 'overdue'),
            ('fleet', 'work_order', 'pending'),
            ('fleet', 'work_order', 'completed'),
            
            # Inventory patterns
            ('inventory', 'low_stock', 'warning'),
            ('inventory', 'low_stock', 'critical'),
            ('inventory', 'reorder', 'needed'),
            
            # HR patterns
            ('hr', 'leave_approval', 'pending'),
            ('hr', 'contract_expiry', '30_days'),
            ('hr', 'contract_expiry', '15_days'),
            
            # System patterns
            ('system', 'test', 'configuration_test'),
        ]
        
        created_count = 0
        
        for template in templates:
            template_name = template.name.lower()
            
            # Try to match against known patterns
            for module, alert_type, alert_level in alert_patterns:
                expected_name = f"{module}_{alert_type}_{alert_level}"
                
                if expected_name in template_name or template_name.replace(' ', '_') == expected_name:
                    # Check if mapping already exists
                    existing = self.template_mapping_ids.filtered(
                        lambda m: m.module_name == module and 
                                 m.alert_type == alert_type and 
                                 m.alert_level == alert_level
                    )
                    
                    if not existing:
                        self.env['gmail.alert.template.mapping'].create({
                            'settings_id': self.id,
                            'module_name': module,
                            'alert_type': alert_type,
                            'alert_level': alert_level,
                            'template_id': template.id,
                            'enabled': True,
                        })
                        created_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Auto-Discovery Complete'),
                'message': _('Created %d template mappings') % created_count,
                'type': 'success',
            }
        }

    # ============================================
    # VALIDATION METHODS
    # ============================================

    @api.constrains('global_recipients', 'summary_recipients', 'admin_notification_email')
    def _validate_email_addresses(self):
        """Validate email address formats"""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        for record in self:
            # Validate global recipients
            if record.global_recipients:
                emails = [email.strip() for email in record.global_recipients.split(',')]
                for email in emails:
                    if email and not email_pattern.match(email):
                        raise ValidationError(
                            _('Invalid email address in Global Recipients: %s') % email
                        )

            # Validate summary recipients
            if record.summary_recipients:
                emails = [email.strip() for email in record.summary_recipients.split(',')]
                for email in emails:
                    if email and not email_pattern.match(email):
                        raise ValidationError(
                            _('Invalid email address in Summary Recipients: %s') % email
                        )

            # Validate admin email
            if record.admin_notification_email:
                if not email_pattern.match(record.admin_notification_email):
                    raise ValidationError(
                        _('Invalid Admin Email address: %s') % record.admin_notification_email
                    )

    @api.constrains('duplicate_prevention_hours', 'batch_interval_minutes', 'cleanup_after_days')
    def _validate_numeric_fields(self):
        """Validate numeric field values"""
        for record in self:
            if record.duplicate_prevention and record.duplicate_prevention_hours <= 0:
                raise ValidationError(_('Prevention window must be greater than 0 hours'))

            if record.batch_processing and record.batch_interval_minutes <= 0:
                raise ValidationError(_('Batch interval must be greater than 0 minutes'))

            if record.auto_cleanup_enabled and record.cleanup_after_days <= 0:
                raise ValidationError(_('Cleanup days must be greater than 0'))

    # ============================================
    # ACTION METHODS
    # ============================================

    def action_test_alert_system(self):
        """Test the alert system"""
        self.ensure_one()

        if not self.system_enabled:
            raise UserError(_('Alert system is disabled. Please enable it first.'))

        if not self.default_account_id:
            raise UserError(_('No default Gmail account configured.'))

        if self.default_account_id.status != 'connected':
            raise UserError(_('Default Gmail account is not connected.'))

        try:
            # Send test alert
            result = self.env['gmail.alert.handler'].send_alert(
                alert_type='system_test',
                alert_level='configuration_test',
                alert_data={
                    'config_name': self.name,
                    'test_time': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'test_user': self.env.user.name,
                    'company_name': self.env.company.name,
                },
                source_module='gmail_alert_settings',
                force_send=True
            )

            # Update test tracking
            self.write({
                'last_test_date': fields.Datetime.now(),
                'last_test_result': f"Success: {result['message']}" if result['success'] else f"Failed: {result['message']}"
            })

            if result['success']:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Test Alert Sent'),
                        'message': _('Test alert sent successfully!'),
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Test Failed'),
                        'message': _('Test failed: %s') % result['message'],
                        'type': 'danger',
                    }
                }

        except Exception as e:
            self.write({
                'last_test_date': fields.Datetime.now(),
                'last_test_result': f'Exception: {str(e)}'
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test Error'),
                    'message': _('Test error: %s') % str(e),
                    'type': 'danger',
                }
            }

    def action_view_alert_logs(self):
        """View alert logs"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Alert Logs'),
            'res_model': 'gmail.alert.handler',
            'view_mode': 'tree,form',
            'context': {'search_default_recent': 1},
        }

    def action_cleanup_alerts(self):
        """Manual cleanup of old alerts"""
        self.ensure_one()

        try:
            count = self.env['gmail.alert.handler'].cleanup_old_alerts(self.cleanup_after_days)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Cleanup Complete'),
                    'message': _('Cleaned up %d old alert records') % count,
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Cleanup Failed'),
                    'message': _('Error: %s') % str(e),
                    'type': 'danger',
                }
            }

    def action_save_and_activate(self):
        """Save and activate this configuration"""
        self.ensure_one()

        # Deactivate other configurations
        other_configs = self.search([('id', '!=', self.id)])
        other_configs.write({'is_active': False})

        # Activate this one
        self.is_active = True

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Configuration Activated'),
                'message': _('Alert system configuration saved and activated!'),
                'type': 'success',
            }
        }

    # ============================================
    # API METHODS FOR ALERT HANDLER
    # ============================================

    @api.model
    def get_active_config(self):
        """Get active alert configuration"""
        config = self.search([('is_active', '=', True)], limit=1)
        if not config:
            # Create default configuration
            config = self.create({
                'name': 'Default Alert Configuration',
                'is_active': True,
            })
        return config

    @api.model
    def is_alert_system_enabled(self):
        """Check if alert system is enabled"""
        config = self.get_active_config()
        return config.system_enabled and config.config_status in ['configured', 'partial']

    @api.model
    def get_default_alert_account(self):
        """Get default alert account"""
        config = self.get_active_config()
        return config.default_account_id if config.system_enabled else None

    @api.model
    def get_global_recipients(self):
        """Get global recipients list"""
        config = self.get_active_config()
        if not config.system_enabled or not config.global_recipients:
            return []

        return [email.strip() for email in config.global_recipients.split(',') if email.strip()]

    @api.model
    def should_prevent_duplicate(self, alert_type, alert_level, alert_data):
        """Check if duplicate should be prevented"""
        config = self.get_active_config()
        return config.duplicate_prevention

    @api.model
    def get_duplicate_prevention_hours(self):
        """Get duplicate prevention window"""
        config = self.get_active_config()
        return config.duplicate_prevention_hours

    @api.model
    def get_template_for_alert_api(self, module_name, alert_type, alert_level=None):
        """API method for Alert Handler to get template"""
        config = self.get_active_config()
        return config.get_template_for_alert(module_name, alert_type, alert_level)

    # ============================================
    # MODEL LIFECYCLE
    # ============================================

    @api.model
    def create(self, vals):
        """Override create to ensure only one active configuration"""
        if vals.get('is_active', False):
            # Deactivate other configurations
            self.search([]).write({'is_active': False})

        return super().create(vals)

    def write(self, vals):
        """Override write to handle active configuration changes"""
        if vals.get('is_active', False):
            # Deactivate other configurations
            other_configs = self.search([('id', 'not in', self.ids)])
            other_configs.write({'is_active': False})

        return super().write(vals)


class GmailAlertTemplateMapping(models.Model):
    """
    Template Mapping for Alert Types
    
    Maps specific alert types to email templates
    Supports any module and alert combination
    """
    _name = 'gmail.alert.template.mapping'
    _description = 'Alert Template Mapping'
    _rec_name = 'display_name'
    _order = 'module_name, alert_type, alert_level'

    # Link to Settings
    settings_id = fields.Many2one(
        'gmail.alert.settings',
        string='Alert Settings',
        required=True,
        ondelete='cascade'
    )

    # Alert Identification
    module_name = fields.Selection([
        ('fleet', 'Fleet Management'),
        ('inventory', 'Inventory'),
        ('hr', 'Human Resources'),
        ('accounting', 'Accounting'),
        ('project', 'Project Management'),
        ('sales', 'Sales'),
        ('purchase', 'Purchase'),
        ('system', 'System'),
        ('custom', 'Custom Module'),
    ], string='Module',
       required=True,
       help='Module generating the alert')

    alert_type = fields.Char(
        string='Alert Type',
        required=True,
        help='Type of alert (e.g., document_expiry, low_stock, work_order)'
    )

    alert_level = fields.Char(
        string='Alert Level',
        help='Specific level/severity (e.g., 30_days, critical, overdue)'
    )

    # Template Selection
    template_id = fields.Many2one(
        'gmail.template',
        string='Email Template',
        required=True,
        help='Template to use for this alert type'
    )

    # Settings
    enabled = fields.Boolean(
        string='Enabled',
        default=True,
        help='Enable/disable this template mapping'
    )

    # Display
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    description = fields.Text(
        string='Description',
        help='Description of when this template is used'
    )

    # ============================================
    # COMPUTED FIELDS
    # ============================================

    @api.depends('module_name', 'alert_type', 'alert_level', 'template_id')
    def _compute_display_name(self):
        """Compute display name"""
        for record in self:
            parts = [record.module_name, record.alert_type]
            if record.alert_level:
                parts.append(record.alert_level)
            
            name = ' → '.join(parts)
            if record.template_id:
                name += f' ({record.template_id.name})'
            
            record.display_name = name

    # ============================================
    # VALIDATION
    # ============================================

    @api.constrains('module_name', 'alert_type', 'alert_level', 'settings_id')
    def _validate_unique_mapping(self):
        """Ensure unique mapping per alert type"""
        for record in self:
            domain = [
                ('settings_id', '=', record.settings_id.id),
                ('module_name', '=', record.module_name),
                ('alert_type', '=', record.alert_type),
                ('alert_level', '=', record.alert_level),
                ('id', '!=', record.id)
            ]
            
            existing = self.search(domain)
            if existing:
                raise ValidationError(
                    _('Template mapping already exists for %s → %s → %s') % 
                    (record.module_name, record.alert_type, record.alert_level or 'General')
                )