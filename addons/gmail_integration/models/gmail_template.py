# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class GmailTemplate(models.Model):
    _name = 'gmail.template'
    _description = 'Gmail Email Template'
    _rec_name = 'name'
    _order = 'name, id desc'

    # Template Information
    name = fields.Char(
        string='Template Name',
        required=True,
        help='Name for this email template'
    )
    description = fields.Text(
        string='Description',
        help='Template description and usage notes'
    )
    
    # Template Content
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
    
    # Recipients
    to_emails = fields.Text(
        string='To (Default)',
        help='Default recipient email addresses (comma separated)'
    )
    cc_emails = fields.Text(
        string='CC (Default)',
        help='Default CC email addresses (comma separated)'
    )
    bcc_emails = fields.Text(
        string='BCC (Default)',
        help='Default BCC email addresses (comma separated)'
    )
    reply_to = fields.Char(
        string='Reply To',
        help='Reply-to email address'
    )
    
    # Template Settings
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether template is available for use'
    )
    is_system = fields.Boolean(
        string='System Template',
        default=False,
        help='System templates cannot be deleted by users'
    )
    
    # Categorization
    category_id = fields.Many2one(
        'gmail.template.category',
        string='Category',
        help='Template category for organization'
    )
    tags = fields.Char(
        string='Tags',
        help='Tags for filtering templates (comma separated)'
    )
    
    # Template Variables
    variable_ids = fields.One2many(
        'gmail.template.variable',
        'template_id',
        string='Variables',
        help='Template variables and their descriptions'
    )
    
    # Usage Statistics
    usage_count = fields.Integer(
        string='Usage Count',
        default=0,
        help='Number of times template has been used'
    )
    last_used_date = fields.Datetime(
        string='Last Used',
        help='When template was last used'
    )
    
    # Template Type - UPDATED WITH system_test
    template_type = fields.Selection([
        ('email', 'Email Template'),
        ('reply', 'Reply Template'),
        ('forward', 'Forward Template'),
        ('auto_reply', 'Auto Reply Template'),
        ('system_test', 'System Test Template'),
    ], string='Type', default='email',
       help='Template type and purpose')
    
    # Account Association
    account_ids = fields.Many2many(
        'gmail.account',
        'gmail_template_account_rel',
        'template_id',
        'account_id',
        string='Gmail Accounts',
        help='Gmail accounts that can use this template'
    )
    
    # Access Control
    user_ids = fields.Many2many(
        'res.users',
        'gmail_template_user_rel',
        'template_id',
        'user_id',
        string='Allowed Users',
        help='Users who can use this template (empty = all users)'
    )
    group_ids = fields.Many2many(
        'res.groups',
        'gmail_template_group_rel',
        'template_id',
        'group_id',
        string='Allowed Groups',
        help='Groups who can use this template'
    )
    
    # Computed Fields
    variable_count = fields.Integer(
        string='Variable Count',
        compute='_compute_variable_count',
        help='Number of variables in template'
    )
    variables_preview = fields.Char(
        string='Variables Preview',
        compute='_compute_variables_preview',
        help='Preview of template variables'
    )
    
    @api.depends('variable_ids')
    def _compute_variable_count(self):
        for record in self:
            record.variable_count = len(record.variable_ids)
    
    @api.depends('variable_ids.name')
    def _compute_variables_preview(self):
        for record in self:
            if record.variable_ids:
                variables = [var.name for var in record.variable_ids[:3]]
                if len(record.variable_ids) > 3:
                    variables.append('...')
                record.variables_preview = ', '.join(variables)
            else:
                record.variables_preview = _('No variables')
    
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
    
    def action_use_template(self):
        """Use template to compose new email"""
        self.ensure_one()
        
        # Update usage statistics
        self.sudo().write({
            'usage_count': self.usage_count + 1,
            'last_used_date': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Compose Email'),
            'res_model': 'gmail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_id': self.id,
                'default_subject': self.subject,
                'default_body_html': self.body_html,
                'default_body_plain': self.body_plain,
                'default_to_emails': self.to_emails,
                'default_cc_emails': self.cc_emails,
                'default_bcc_emails': self.bcc_emails,
                'default_reply_to': self.reply_to,
            }
        }
    
    def action_preview_template(self):
        """Preview template with sample data"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Template Preview'),
            'res_model': 'gmail.template.preview',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_id': self.id,
            }
        }
    
    def action_duplicate_template(self):
        """Create a copy of this template"""
        self.ensure_one()
        
        copy_vals = {
            'name': _('%s (Copy)') % self.name,
            'is_system': False,  # Copies are never system templates
        }
        
        new_template = self.copy(copy_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Template Copy'),
            'res_model': 'gmail.template',
            'view_mode': 'form',
            'res_id': new_template.id,
            'target': 'current',
        }
    
    def get_rendered_content(self, variables=None):
        """Render template content with variables"""
        self.ensure_one()
        
        if variables is None:
            variables = {}
        
        # Add default variables
        default_vars = {
            'user_name': self.env.user.name,
            'company_name': self.env.company.name,
            'current_date': fields.Date.today().strftime('%Y-%m-%d'),
            'current_time': fields.Datetime.now().strftime('%H:%M:%S'),
        }
        variables.update(default_vars)
        
        # Render subject
        subject = self.subject or ''
        for var_name, var_value in variables.items():
            subject = subject.replace(f'{{{{{var_name}}}}}', str(var_value))
        
        # Render HTML body
        body_html = self.body_html or ''
        for var_name, var_value in variables.items():
            body_html = body_html.replace(f'{{{{{var_name}}}}}', str(var_value))
        
        # Render plain body
        body_plain = self.body_plain or ''
        for var_name, var_value in variables.items():
            body_plain = body_plain.replace(f'{{{{{var_name}}}}}', str(var_value))
        
        return {
            'subject': subject,
            'body_html': body_html,
            'body_plain': body_plain,
        }
    
    def extract_variables_from_content(self):
        """Extract variable names from template content"""
        self.ensure_one()
        
        # Find variables in format {{variable_name}}
        variable_pattern = re.compile(r'\{\{(\w+)\}\}')
        
        variables = set()
        
        # Search in subject
        if self.subject:
            variables.update(variable_pattern.findall(self.subject))
        
        # Search in HTML body
        if self.body_html:
            variables.update(variable_pattern.findall(self.body_html))
        
        # Search in plain body
        if self.body_plain:
            variables.update(variable_pattern.findall(self.body_plain))
        
        return sorted(list(variables))
    
    def action_auto_create_variables(self):
        """Automatically create variable records from content"""
        self.ensure_one()
        
        existing_vars = {var.name for var in self.variable_ids}
        content_vars = set(self.extract_variables_from_content())
        
        new_vars = content_vars - existing_vars
        
        if new_vars:
            for var_name in new_vars:
                self.env['gmail.template.variable'].create({
                    'template_id': self.id,
                    'name': var_name,
                    'description': f'Auto-generated variable: {var_name}',
                })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Variables Created'),
                    'message': _('Created %d new variables') % len(new_vars),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No New Variables'),
                    'message': _('All variables are already defined'),
                    'type': 'info',
                }
            }
    
    @api.model
    def create_system_templates(self):
        """Create default system templates"""
        system_templates = [
            {
                'name': 'Welcome Email',
                'subject': 'Welcome to {{company_name}}!',
                'body_html': '''
                    <p>Hello {{contact_name}},</p>
                    <p>Welcome to {{company_name}}! We're excited to have you on board.</p>
                    <p>Best regards,<br/>{{user_name}}</p>
                ''',
                'template_type': 'email',
                'is_system': True,
            },
            {
                'name': 'Meeting Follow-up',
                'subject': 'Follow-up: {{meeting_subject}}',
                'body_html': '''
                    <p>Hello {{contact_name}},</p>
                    <p>Thank you for taking the time to meet with us regarding {{meeting_subject}}.</p>
                    <p>As discussed, next steps are:</p>
                    <ul>
                        <li>{{next_step_1}}</li>
                        <li>{{next_step_2}}</li>
                    </ul>
                    <p>Best regards,<br/>{{user_name}}</p>
                ''',
                'template_type': 'email',
                'is_system': True,
            },
            {
                'name': 'Thank You Reply',
                'subject': 'Re: {{original_subject}}',
                'body_html': '''
                    <p>Thank you for your email.</p>
                    <p>{{custom_message}}</p>
                    <p>Best regards,<br/>{{user_name}}</p>
                ''',
                'template_type': 'reply',
                'is_system': True,
            }
        ]
        
        for template_data in system_templates:
            existing = self.search([
                ('name', '=', template_data['name']),
                ('is_system', '=', True)
            ])
            if not existing:
                self.create(template_data)


class GmailTemplateCategory(models.Model):
    _name = 'gmail.template.category'
    _description = 'Gmail Template Category'
    _rec_name = 'name'
    _order = 'sequence, name'

    name = fields.Char(
        string='Category Name',
        required=True,
        help='Name of the template category'
    )
    description = fields.Text(
        string='Description',
        help='Category description'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order sequence for display'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether category is active'
    )
    color = fields.Integer(
        string='Color',
        default=0,
        help='Category color for UI display'
    )
    
    # Relations
    template_ids = fields.One2many(
        'gmail.template',
        'category_id',
        string='Templates',
        help='Templates in this category'
    )
    
    # Computed Fields
    template_count = fields.Integer(
        string='Template Count',
        compute='_compute_template_count',
        help='Number of templates in category'
    )
    
    @api.depends('template_ids')
    def _compute_template_count(self):
        for record in self:
            record.template_count = len(record.template_ids)


class GmailTemplateVariable(models.Model):
    _name = 'gmail.template.variable'
    _description = 'Gmail Template Variable'
    _rec_name = 'name'
    _order = 'sequence, name'

    # Template Reference
    template_id = fields.Many2one(
        'gmail.template',
        string='Template',
        required=True,
        ondelete='cascade',
        help='Associated template'
    )
    
    # Variable Information
    name = fields.Char(
        string='Variable Name',
        required=True,
        help='Variable name (without curly braces)'
    )
    description = fields.Text(
        string='Description',
        help='Description of what this variable represents'
    )
    default_value = fields.Char(
        string='Default Value',
        help='Default value for this variable'
    )
    
    # Variable Type
    variable_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('datetime', 'Date/Time'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('partner', 'Partner'),
        ('user', 'User'),
    ], string='Type', default='text',
       help='Variable data type')
    
    # Display
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order sequence for display'
    )
    is_required = fields.Boolean(
        string='Required',
        default=False,
        help='Whether variable is required when using template'
    )
    
    # Validation
    validation_pattern = fields.Char(
        string='Validation Pattern',
        help='Regex pattern for validating variable value'
    )
    validation_message = fields.Char(
        string='Validation Message',
        help='Error message for validation failures'
    )
    
    @api.constrains('name')
    def _check_variable_name(self):
        """Validate variable name format"""
        for record in self:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', record.name):
                raise ValidationError(
                    _('Variable name must start with letter or underscore and contain only letters, numbers, and underscores')
                )
    
    @api.constrains('name', 'template_id')
    def _check_unique_name(self):
        """Ensure variable names are unique within template"""
        for record in self:
            existing = self.search([
                ('name', '=', record.name),
                ('template_id', '=', record.template_id.id),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(
                    _('Variable name "%s" already exists in this template') % record.name
                )
