# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class GmailAccountSwitcher(models.TransientModel):
    _name = 'gmail.account.switcher'
    _description = 'Gmail Account Switcher Wizard'

    current_account_id = fields.Many2one(
        'gmail.account',
        string='Current Account',
        readonly=True,
        help='Currently active Gmail account'
    )
    
    current_account_name = fields.Char(
        related='current_account_id.name',
        readonly=True,
        string='Current Account Name'
    )
    
    current_account_email = fields.Char(
        related='current_account_id.email_address',
        readonly=True,
        string='Current Account Email'
    )
    
    current_account_initial = fields.Char(
        string='Current Account Initial',
        compute='_compute_current_account_initial',
        readonly=True
    )
    
    selected_account_id = fields.Many2one(
        'gmail.account',
        string='Switch To',
        help='Select the Gmail account to switch to'
    )
    
    available_account_ids = fields.Many2many(
        'gmail.account',
        string='Available Accounts',
        help='Accounts available to current user'
    )
    
    other_accounts = fields.One2many(
        'gmail.account.switch.line',
        'switcher_id',
        string='Other Accounts',
        compute='_compute_other_accounts',
        store=False
    )

    @api.depends('current_account_name')
    def _compute_current_account_initial(self):
        """Compute the first letter of current account name for avatar"""
        for record in self:
            if record.current_account_name:
                record.current_account_initial = record.current_account_name[0].upper()
            else:
                record.current_account_initial = '?'

    @api.depends('current_account_id', 'available_account_ids')
    def _compute_other_accounts(self):
        """Compute other available accounts (excluding current)"""
        for record in self:
            # Clear existing lines first
            record.other_accounts = [(5, 0, 0)]
            
            # Get current account ID
            current_id = record.current_account_id.id if record.current_account_id else 0
            
            # Debug logging
            _logger.info(f'Computing other accounts for record {record.id}:')
            _logger.info(f'  - Current account: {record.current_account_id} (ID: {current_id})')
            _logger.info(f'  - Available accounts: {record.available_account_ids}')
            _logger.info(f'  - Available account IDs: {record.available_account_ids.ids}')
            
            # Get other accounts (not current and only connected ones)
            if current_id and record.available_account_ids:
                other_account_ids = record.available_account_ids.filtered(
                    lambda a: a.id != current_id and a.status in ['connected', 'active']
                )
            else:
                # If no current account, show all available accounts
                other_account_ids = record.available_account_ids.filtered(
                    lambda a: a.status in ['connected', 'active']
                )
            
            _logger.info(f'  - Filtered other accounts: {other_account_ids}')
            _logger.info(f'  - Other account IDs: {other_account_ids.ids}')
            
            # Create switch lines for other accounts
            lines = []
            for account in other_account_ids:
                lines.append((0, 0, {
                    'account_id': account.id,
                    'switcher_id': record.id,
                }))
            
            record.other_accounts = lines
            _logger.info(f'  - Created {len(lines)} other account lines')

    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super().default_get(fields_list)
        
        context = self.env.context
        
        # Set current account
        if context.get('default_current_account_id'):
            res['current_account_id'] = context['default_current_account_id']
            _logger.info(f'Switcher: Set current account from context: {res["current_account_id"]}')
        
        # Set available accounts
        if context.get('available_account_ids'):
            res['available_account_ids'] = [(6, 0, context['available_account_ids'])]
        else:
            # Fallback: get all connected accounts for current user
            accounts = self.env['gmail.account'].search([
                ('status', 'in', ['connected', 'active']),
                '|', '|', '|',
                ('user_id', '=', self.env.user.id),
                '&', ('access_level', '=', 'shared'), ('shared_user_ids', 'in', [self.env.user.id]),
                '&', ('access_level', '=', 'company'), ('user_id.company_id', '=', self.env.user.company_id.id),
                ('access_level', '=', 'company')
            ])
            res['available_account_ids'] = [(6, 0, accounts.ids)]
            _logger.info(f'Switcher: Found available accounts: {accounts.ids}')
        
        _logger.info(f'Switcher default_get result: Current={res.get("current_account_id")}, Available={res.get("available_account_ids")}')
        
        return res

    def action_switch_account(self):
        """Switch to selected account"""
        if not self.selected_account_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Account Selected'),
                    'message': _('Please select an account to switch to.'),
                    'type': 'warning',
                }
            }
        
        try:
            # Use the dashboard's force refresh method
            dashboard = self.env['gmail.dashboard']
            result = dashboard.force_dashboard_refresh_with_account(self.selected_account_id.id)
            
            if result.get('success'):
                # Close the modal and return the dashboard action
                return {
                    'type': 'ir.actions.act_window_close',
                    'effect': {
                        'type': 'rainbow_man',
                        'message': _('Successfully switched to %s') % self.selected_account_id.email_address,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Switch Failed'),
                        'message': _('Failed to switch account: %s') % result.get('error', 'Unknown error'),
                        'type': 'danger',
                    }
                }
                
        except Exception as e:
            _logger.error(f'Error switching account: {e}')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Switch Failed'),
                    'message': _('Failed to switch account: %s') % str(e),
                    'type': 'danger',
                }
            }

    def action_sign_out_current(self):
        """Sign out from current account"""
        if not self.current_account_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Account'),
                    'message': _('No current account to sign out from.'),
                    'type': 'warning',
                }
            }
        
        try:
            # Store email for notification
            account_email = self.current_account_id.email_address
            
            # Clear OAuth tokens for current account
            self.current_account_id.write({
                'access_token': False,
                'refresh_token': False,
                'status': 'disconnected',
                'last_oauth_date': False,
            })
            
            # Clear from session if dashboard method exists
            try:
                dashboard = self.env['gmail.dashboard']
                dashboard_record = dashboard.create({})
                if hasattr(dashboard_record, '_set_session_active_account'):
                    dashboard_record._set_session_active_account(None)
            except:
                pass  # Dashboard method might not exist
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Signed Out'),
                    'message': _('Successfully signed out from %s') % account_email,
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f'Error signing out account: {e}')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sign Out Failed'),
                    'message': _('Failed to sign out: %s') % str(e),
                    'type': 'danger',
                }
            }

    def action_add_account(self):
        """Action to add new Gmail account"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Gmail Account'),
            'res_model': 'gmail.account',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'create': True,
                'default_user_id': self.env.user.id
            },
        }


class GmailAccountSwitchLine(models.TransientModel):
    _name = 'gmail.account.switch.line'
    _description = 'Gmail Account Switch Line'
    _order = 'account_name'
    
    switcher_id = fields.Many2one(
        'gmail.account.switcher',
        string='Switcher',
        required=True,
        ondelete='cascade'
    )
    
    account_id = fields.Many2one(
        'gmail.account',
        string='Gmail Account',
        required=True
    )
    
    account_name = fields.Char(
        related='account_id.name',
        readonly=True,
        string='Account Name'
    )
    
    account_email = fields.Char(
        related='account_id.email_address',
        readonly=True,
        string='Account Email'
    )
    
    account_status = fields.Selection(
        related='account_id.status',
        readonly=True,
        string='Account Status'
    )
    
    is_current = fields.Boolean(
        string='Current',
        default=False,
        help='Is this the currently active account'
    )
    
    unread_count = fields.Integer(
        string='Unread Count',
        compute='_compute_unread_count',
        help='Number of unread messages'
    )
    
    # Add computed field for avatar initial
    avatar_initial = fields.Char(
        string='Avatar Initial',
        compute='_compute_avatar_initial'
    )
    
    @api.depends('account_name')
    def _compute_avatar_initial(self):
        """Compute the first letter of account name for avatar"""
        for line in self:
            if line.account_name:
                line.avatar_initial = line.account_name[0].upper()
            else:
                line.avatar_initial = '?'
    
    @api.depends('account_id')
    def _compute_unread_count(self):
        """Compute unread message count"""
        for line in self:
            if line.account_id:
                try:
                    # Try to get unread count from gmail.message model
                    line.unread_count = self.env['gmail.message'].search_count([
                        ('account_id', '=', line.account_id.id),
                        ('is_read', '=', False),
                        ('direction', '=', 'inbound')
                    ])
                except:
                    # Fallback if gmail.message model doesn't exist or has different structure
                    line.unread_count = 0
            else:
                line.unread_count = 0

    def action_switch_to_this_account(self):
        """Switch to this account - Called from JavaScript"""
        if not self.account_id:
            return {
                'success': False, 
                'error': 'No account specified'
            }
        
        try:
            # Use the dashboard's force refresh method
            dashboard = self.env['gmail.dashboard']
            result = dashboard.force_dashboard_refresh_with_account(self.account_id.id)
            
            if result.get('success'):
                return {
                    'success': True,
                    'message': f'Switched to {self.account_email}',
                    'action': result.get('action', {}),
                    'account_email': self.account_email,
                    'account_name': self.account_name,
                    'reload_page': True  # Signal to reload the page
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            _logger.error(f'Error in switch line action: {e}')
            return {
                'success': False, 
                'error': str(e)
            }

    def switch_account(self):
        """Alternative method name for account switching"""
        return self.action_switch_to_this_account()

    def signout_account(self):
        """Sign out this specific account"""
        try:
            # Store email for notification
            account_email = self.account_email
            
            # Clear OAuth tokens
            self.account_id.write({
                'access_token': False,
                'refresh_token': False,
                'status': 'disconnected',
                'last_oauth_date': False,
            })
            
            # Refresh the switcher view
            self.switcher_id._compute_other_accounts()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Account Signed Out'),
                    'message': _('Successfully signed out from %s') % account_email,
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f'Error signing out line account: {e}')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sign Out Failed'),
                    'message': _('Failed to sign out: %s') % str(e),
                    'type': 'danger',
                }
            }
