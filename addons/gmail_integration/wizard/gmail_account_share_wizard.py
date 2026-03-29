# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class GmailAccountShareWizard(models.TransientModel):
    _name = 'gmail.account.share.wizard'
    _description = 'Gmail Account Sharing Wizard'

    # Related Account
    account_id = fields.Many2one(
        'gmail.account',
        string='Gmail Account',
        required=True,
        readonly=True
    )
    
    account_name = fields.Char(
        related='account_id.name',
        readonly=True
    )
    
    email_address = fields.Char(
        related='account_id.email_address', 
        readonly=True
    )
    
    current_owner = fields.Many2one(
        related='account_id.user_id',
        readonly=True
    )
    
    # Sharing Configuration
    access_level = fields.Selection([
        ('private', 'Private (Owner Only)'),
        ('shared', 'Shared with Selected Users'), 
        ('company', 'Company Wide'),
    ], string='Access Level',
       required=True,
       help='Who can access this Gmail account')
    
    shared_user_ids = fields.Many2many(
        'res.users',
        string='Share With Users',
        help='Users who will have access to this Gmail account',
        domain="[('id', '!=', current_owner)]"
    )
    
    # Permission Levels
    allow_send_emails = fields.Boolean(
        string='Allow Sending Emails', 
        default=True,
        help='Allow shared users to send emails from this account'
    )
    
    allow_manage_settings = fields.Boolean(
        string='Allow Managing Settings',
        default=False, 
        help='Allow shared users to modify account settings'
    )
    
    # Information and Status
    current_shared_users = fields.Many2many(
        related='account_id.shared_user_ids',
        readonly=True
    )
    
    warning_message = fields.Text(
        string='Warning',
        compute='_compute_warning_message'
    )
    
    @api.depends('access_level', 'shared_user_ids', 'account_id')
    def _compute_warning_message(self):
        for record in self:
            warnings = []
            
            if record.access_level == 'shared' and not record.shared_user_ids:
                warnings.append('Please select users to share this account with.')
            
            if record.access_level == 'company':
                company_users = self.env['res.users'].search([
                    ('company_id', '=', record.current_owner.company_id.id),
                    ('id', '!=', record.current_owner.id)
                ])
                if company_users:
                    warnings.append(f'This will share the account with all {len(company_users)} users in your company.')
            
            if record.access_level != 'private' and record.account_id:
                warnings.append('Shared users will be able to read all emails in this account.')
            
            record.warning_message = '\n'.join(warnings) if warnings else False
    
    @api.onchange('access_level')
    def _onchange_access_level(self):
        if self.access_level != 'shared':
            self.shared_user_ids = [(5, 0, 0)]  # Clear selected users
    
    @api.constrains('access_level', 'shared_user_ids')
    def _check_shared_users(self):
        for record in self:
            if record.access_level == 'shared' and not record.shared_user_ids:
                raise ValidationError(_('Please select users to share this account with when using "Shared" access level.'))
    
    def action_apply_sharing(self):
        """Apply sharing configuration to the Gmail account"""
        self.ensure_one()
        
        if not self.account_id:
            raise UserError(_('Gmail account not found'))
        
        # Check if user is owner or admin
        if self.account_id.user_id != self.env.user and not self.env.user.has_group('base.group_system'):
            raise UserError(_('Only the account owner or administrators can modify sharing settings'))
        
        # Prepare values to update
        values = {
            'access_level': self.access_level,
        }
        
        # Handle shared users
        if self.access_level == 'shared':
            values['shared_user_ids'] = [(6, 0, self.shared_user_ids.ids)]
        else:
            values['shared_user_ids'] = [(5, 0, 0)]  # Clear shared users
        
        # Update the account
        self.account_id.sudo().write(values)
        
        # Log the change
        message = self._get_sharing_change_message()
        self.account_id.message_post(
            body=message,
            subject='Account Sharing Updated',
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sharing Updated'),
                'message': _('Gmail account sharing settings have been updated successfully.'),
                'type': 'success',
            }
        }
    
    def _get_sharing_change_message(self):
        """Generate message describing the sharing change"""
        messages = []
        
        if self.access_level == 'private':
            messages.append('Account is now private (owner only access)')
        elif self.access_level == 'shared':
            user_names = ', '.join(self.shared_user_ids.mapped('name'))
            messages.append(f'Account is now shared with: {user_names}')
        elif self.access_level == 'company':
            messages.append(f'Account is now shared company-wide ({self.current_owner.company_id.name})')
        
        return '<br/>'.join(messages)
    
    def action_preview_access(self):
        """Preview who will have access to this account"""
        self.ensure_one()
        
        if self.access_level == 'private':
            users = self.current_owner
        elif self.access_level == 'shared':
            users = self.current_owner | self.shared_user_ids
        elif self.access_level == 'company':
            users = self.env['res.users'].search([
                ('company_id', '=', self.current_owner.company_id.id)
            ])
        else:
            users = self.env['res.users']
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Users with Access'),
            'res_model': 'res.users',
            'view_mode': 'tree',
            'domain': [('id', 'in', users.ids)],
            'target': 'new',
            'context': {'create': False, 'edit': False, 'delete': False}
        }
