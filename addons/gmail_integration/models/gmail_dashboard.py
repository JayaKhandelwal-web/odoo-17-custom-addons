# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.http import request
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class GmailDashboard(models.TransientModel):
    _name = 'gmail.dashboard'
    _description = 'Gmail Dashboard with Account Switching'

    # Active Account Selection
    active_account_id = fields.Many2one(
        'gmail.account',
        string='Active Gmail Account',
        help='Currently selected Gmail account for dashboard view'
    )
    
    # Available Accounts for User
    available_account_ids = fields.Many2many(
        'gmail.account',
        compute='_compute_available_accounts',
        string='Available Accounts',
        help='Gmail accounts accessible by current user'
    )
    
    # Account Display Info
    active_account_name = fields.Char(
        string='Account Name',
        related='active_account_id.name',
        readonly=True
    )
    
    active_account_email = fields.Char(
        string='Account Email',
        related='active_account_id.email_address',
        readonly=True
    )
    
    active_account_status = fields.Selection(
        related='active_account_id.status',
        readonly=True
    )

    # Dashboard Statistics (Account-Specific)
    total_messages = fields.Integer(
        string='Total Messages',
        compute='_compute_statistics',
        help='Total number of messages for active account'
    )
    
    unread_messages = fields.Integer(
        string='Unread Messages',
        compute='_compute_statistics',
        help='Number of unread messages for active account'
    )
    
    sent_today = fields.Integer(
        string='Sent Today',
        compute='_compute_statistics',
        help='Messages sent today from active account'
    )
    
    total_accounts = fields.Integer(
        string='Total Accounts',
        compute='_compute_statistics',
        help='Number of accessible Gmail accounts'
    )
    
    # Account-Specific Message Lists
    latest_messages = fields.Many2many(
        'gmail.message',
        compute='_compute_latest_messages',
        string='Latest Messages',
        help='Latest inbox messages for active account'
    )

    @api.depends()
    def _compute_available_accounts(self):
        """Get accounts accessible by current user"""
        for record in self:
            accounts = self.env['gmail.account'].search([
                '|', '|', '|',
                ('user_id', '=', self.env.user.id),
                '&', ('access_level', '=', 'shared'), ('shared_user_ids', 'in', [self.env.user.id]),
                '&', ('access_level', '=', 'company'), ('user_id.company_id', '=', self.env.user.company_id.id),
                ('access_level', '=', 'company')
            ])
            record.available_account_ids = accounts

    @api.depends('active_account_id')
    def _compute_statistics(self):
        """Compute dashboard statistics for active account"""
        for record in self:
            if not record.active_account_id:
                record.total_messages = 0
                record.unread_messages = 0
                record.sent_today = 0
                record.total_accounts = len(record.available_account_ids)
                continue

            try:
                message_model = self.env['gmail.message']
                account_domain = [('account_id', '=', record.active_account_id.id)]
                
                record.total_messages = message_model.search_count(account_domain)
                record.unread_messages = message_model.search_count(
                    account_domain + [('is_read', '=', False)]
                )
                
                today_start = datetime.combine(date.today(), datetime.min.time())
                today_end = datetime.combine(date.today(), datetime.max.time())
                
                record.sent_today = message_model.search_count(
                    account_domain + [
                        ('direction', '=', 'outbound'),
                        ('date', '>=', today_start),
                        ('date', '<=', today_end)
                    ]
                )
                
                record.total_accounts = len(record.available_account_ids)
                
            except Exception as e:
                _logger.error(f'Error computing statistics: {e}')
                record.total_messages = 0
                record.unread_messages = 0
                record.sent_today = 0
                record.total_accounts = len(record.available_account_ids)

    @api.depends('active_account_id')
    def _compute_latest_messages(self):
        """Get latest inbox messages for active account"""
        for record in self:
            if not record.active_account_id:
                record.latest_messages = self.env['gmail.message']
                continue

            try:
                latest = self.env['gmail.message'].search([
                    ('account_id', '=', record.active_account_id.id),
                    ('direction', '=', 'inbound')
                ], limit=20, order='date desc')
                
                record.latest_messages = latest
                
            except Exception as e:
                _logger.error(f'Error getting latest messages: {e}')
                record.latest_messages = self.env['gmail.message']

    @api.model
    def default_get(self, fields_list):
        """Set default active account with proper session and URL parameter handling - ENHANCED"""
        res = super().default_get(fields_list)
        
        # Priority 1: Check for forced account ID (after switch)
        force_account_id = self.env.context.get('force_active_account_id')
        if force_account_id:
            _logger.info(f'Dashboard: Using forced account ID: {force_account_id}')
            res['active_account_id'] = force_account_id
            self._set_session_active_account(force_account_id)
            return res
        
        # Priority 2: Check URL parameters (NEW - this fixes the switching)
        try:
            if hasattr(request, 'params') and request.params.get('active_account_id'):
                url_account_id = int(request.params.get('active_account_id'))
                _logger.info(f'Dashboard: Using URL account ID: {url_account_id}')
                res['active_account_id'] = url_account_id
                self._set_session_active_account(url_account_id)
                return res
        except:
            pass
        
        # Priority 3: Check if account ID is in the action context (NEW)
        action_context = self.env.context
        if action_context.get('active_account_id'):
            context_account_id = action_context.get('active_account_id')
            _logger.info(f'Dashboard: Using context account ID: {context_account_id}')
            res['active_account_id'] = context_account_id
            self._set_session_active_account(context_account_id)
            return res
        
        # Priority 4: Get session account
        session_account_id = self._get_session_active_account()
        _logger.info(f'Dashboard: Session account ID: {session_account_id}')
        
        # Get user's accessible accounts
        accounts = self.env['gmail.account'].search([
            '|', '|', '|',
            ('user_id', '=', self.env.user.id),
            '&', ('access_level', '=', 'shared'), ('shared_user_ids', 'in', [self.env.user.id]),
            '&', ('access_level', '=', 'company'), ('user_id.company_id', '=', self.env.user.company_id.id),
            ('access_level', '=', 'company')
        ])
        
        if accounts:
            if session_account_id and session_account_id in accounts.ids:
                res['active_account_id'] = session_account_id
                _logger.info(f'Dashboard: Using session account: {session_account_id}')
            else:
                # Fallback to most recent connected account
                connected_accounts = accounts.filtered(lambda a: a.status == 'connected')
                if connected_accounts:
                    recent_account = connected_accounts.sorted('last_oauth_date', reverse=True)[0]
                    res['active_account_id'] = recent_account.id
                    self._set_session_active_account(recent_account.id)
                    _logger.info(f'Dashboard: Using recent account: {recent_account.id}')
                else:
                    # Fallback to first account
                    res['active_account_id'] = accounts[0].id
                    self._set_session_active_account(accounts[0].id)
                    _logger.info(f'Dashboard: Using first account: {accounts[0].id}')
        
        return res

    def _get_session_active_account(self):
        """Get active account from session"""
        try:
            if request and hasattr(request, 'session'):
                return request.session.get('gmail_active_account_id')
        except:
            pass
        return None

    def _set_session_active_account(self, account_id):
        """Set active account in session"""
        try:
            if request and hasattr(request, 'session'):
                request.session['gmail_active_account_id'] = account_id
                _logger.info(f'Session updated: gmail_active_account_id = {account_id}')
        except Exception as e:
            _logger.error(f'Error setting session: {e}')

    @api.model
    def force_dashboard_refresh_with_account(self, account_id):
        """Force dashboard refresh with specific account - ENHANCED VERSION"""
        try:
            _logger.info(f'Force refresh requested for account: {account_id}')
            
            # Verify account access with proper domain
            account = self.env['gmail.account'].search([
                ('id', '=', account_id),
                '|', '|', '|',
                ('user_id', '=', self.env.user.id),
                '&', ('access_level', '=', 'shared'), ('shared_user_ids', 'in', [self.env.user.id]),
                '&', ('access_level', '=', 'company'), ('user_id.company_id', '=', self.env.user.company_id.id),
                ('access_level', '=', 'company')
            ])
            
            if not account:
                _logger.error(f'Account {account_id} not accessible by user {self.env.user.id}')
                return {'success': False, 'error': 'Account not accessible'}
            
            # Set session to new account
            self._set_session_active_account(account_id)
            _logger.info(f'Session updated for account: {account.email_address}')
            
            # Return action to reload dashboard with new account
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Gmail Dashboard',
                'res_model': 'gmail.dashboard',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'force_active_account_id': account_id,
                    'active_account_switched': True
                },
                'flags': {
                    'clear_breadcrumbs': True,
                    'headless': True
                }
            }
            
            # Return success with action and account info
            result = {
                'success': True, 
                'account_email': account.email_address,
                'account_name': account.name,
                'account_id': account_id,
                'action': action,
                'message': f'Successfully switched to {account.email_address}'
            }
            
            _logger.info(f'Account switch successful: {result}')
            return result
            
        except Exception as e:
            _logger.error(f'Error in force refresh: {e}', exc_info=True)
            return {'success': False, 'error': str(e)}

    def action_switch_account(self):
        """Open account switcher wizard"""
        current_account_id = self.active_account_id.id if self.active_account_id else False
        available_account_ids = self.available_account_ids.ids
        
        _logger.info(f'Dashboard: Opening switcher - Current: {current_account_id}, Available: {available_account_ids}')
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Switch Gmail Account'),
            'res_model': 'gmail.account.switcher',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_current_account_id': current_account_id,
                'available_account_ids': available_account_ids,
            }
        }

    def action_view_inbox(self):
        """Open inbox view for active account"""
        if not self.active_account_id:
            return self._show_no_account_warning()
            
        return {
            'type': 'ir.actions.act_window',
            'name': f'Inbox - {self.active_account_email}',
            'res_model': 'gmail.message',
            'view_mode': 'tree,form',
            'domain': [
                ('account_id', '=', self.active_account_id.id),
                ('direction', '=', 'inbound')
            ],
            'context': {
                'search_default_unread': 1,
                'active_account_id': self.active_account_id.id,
                'active_account_name': self.active_account_name,
            },
        }

    def action_view_sent(self):
        """Open sent messages view for active account"""
        if not self.active_account_id:
            return self._show_no_account_warning()
            
        return {
            'type': 'ir.actions.act_window',
            'name': f'Sent - {self.active_account_email}',
            'res_model': 'gmail.message',
            'view_mode': 'tree,form',
            'domain': [
                ('account_id', '=', self.active_account_id.id),
                ('direction', '=', 'outbound')
            ],
            'context': {
                'active_account_id': self.active_account_id.id,
                'active_account_name': self.active_account_name,
            },
        }

    def action_view_drafts(self):
        """Open drafts view for active account"""
        if not self.active_account_id:
            return self._show_no_account_warning()
            
        return {
            'type': 'ir.actions.act_window',
            'name': f'Drafts - {self.active_account_email}',
            'res_model': 'gmail.message',
            'view_mode': 'tree,form',
            'domain': [
                ('account_id', '=', self.active_account_id.id),
                ('direction', '=', 'draft')
            ],
            'context': {
                'active_account_id': self.active_account_id.id,
                'active_account_name': self.active_account_name,
            },
        }

    def action_view_all_messages(self):
        """Open all messages view for active account"""
        if not self.active_account_id:
            return self._show_no_account_warning()
            
        return {
            'type': 'ir.actions.act_window',
            'name': f'All Messages - {self.active_account_email}',
            'res_model': 'gmail.message',
            'view_mode': 'tree,form',
            'domain': [('account_id', '=', self.active_account_id.id)],
            'context': {
                'active_account_id': self.active_account_id.id,
                'active_account_name': self.active_account_name,
            },
        }

    def action_view_accounts(self):
        """Open Gmail accounts view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'My Gmail Accounts',
            'res_model': 'gmail.account',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.available_account_ids.ids)],
            'context': {'create': True},
        }

    def action_send_new_mail(self):
        """Open compose mail wizard for active account"""
        if not self.active_account_id:
            return self._show_no_account_warning()
            
        return {
            'type': 'ir.actions.act_window',
            'name': f'Compose Email - {self.active_account_name}',
            'res_model': 'gmail.send.mail',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_account_id': self.active_account_id.id,
            }
        }

    def action_sync_active_account(self):
        """Sync emails for active account"""
        if not self.active_account_id:
            return self._show_no_account_warning()
            
        if self.active_account_id.status != 'connected':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Account Not Connected'),
                    'message': _('Please connect the Gmail account first.'),
                    'type': 'warning',
                }
            }
        
        try:
            self.active_account_id.action_sync_now()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sync Started'),
                    'message': _('Email synchronization started for %s') % self.active_account_email,
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sync Failed'),
                    'message': _('Failed to sync %s: %s') % (self.active_account_email, str(e)),
                    'type': 'danger',
                }
            }

    def _show_no_account_warning(self):
        """Show warning when no account is selected"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('No Account Selected'),
                'message': _('Please select a Gmail account first.'),
                'type': 'warning',
            }
        }
