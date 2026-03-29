# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class GmailSyncLog(models.Model):
    _name = 'gmail.sync.log'
    _description = 'Gmail Sync Log'
    _rec_name = 'display_name'
    _order = 'start_time desc, id desc'

    # Account Reference
    account_id = fields.Many2one(
        'gmail.account',
        string='Gmail Account',
        required=True,
        ondelete='cascade',
        help='Associated Gmail account'
    )
    
    # Sync Information
    sync_type = fields.Selection([
        ('full', 'Full Sync'),
        ('incremental', 'Incremental Sync'),
        ('manual', 'Manual Sync'),
        ('realtime', 'Real-time Sync'),
        ('webhook', 'Webhook Triggered'),
    ], string='Sync Type', required=True,
       help='Type of synchronization')
    
    # Timing
    start_time = fields.Datetime(
        string='Start Time',
        required=True,
        default=fields.Datetime.now,
        help='When sync started'
    )
    end_time = fields.Datetime(
        string='End Time',
        help='When sync completed'
    )
    duration = fields.Float(
        string='Duration (seconds)',
        compute='_compute_duration',
        store=True,
        help='Sync duration in seconds'
    )
    
    # Status
    status = fields.Selection([
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('partial', 'Partial Success'),
    ], string='Status', default='running',
       help='Sync status')
    
    # Statistics
    messages_processed = fields.Integer(
        string='Messages Processed',
        default=0,
        help='Number of messages processed'
    )
    messages_created = fields.Integer(
        string='Messages Created',
        default=0,
        help='Number of new messages created'
    )
    messages_updated = fields.Integer(
        string='Messages Updated',
        default=0,
        help='Number of messages updated'
    )
    messages_failed = fields.Integer(
        string='Messages Failed',
        default=0,
        help='Number of messages that failed to sync'
    )
    
    # API Usage
    api_calls_made = fields.Integer(
        string='API Calls Made',
        default=0,
        help='Number of Gmail API calls made'
    )
    quota_used = fields.Integer(
        string='Quota Used',
        default=0,
        help='Gmail API quota consumed'
    )
    
    # Error Information
    error_message = fields.Text(
        string='Error Message',
        help='Error message if sync failed'
    )
    error_details = fields.Text(
        string='Error Details',
        help='Detailed error information (JSON)'
    )
    
    # Sync Details
    sync_details = fields.Text(
        string='Sync Details',
        help='Additional sync information (JSON)'
    )
    
    # Display Name
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        help='Computed display name'
    )
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                duration = (record.end_time - record.start_time).total_seconds()
                record.duration = duration
            else:
                record.duration = 0.0
    
    @api.depends('account_id', 'sync_type', 'start_time', 'status')
    def _compute_display_name(self):
        for record in self:
            account_name = record.account_id.name if record.account_id else 'Unknown'
            sync_type = dict(record._fields['sync_type'].selection).get(record.sync_type, record.sync_type)
            status = dict(record._fields['status'].selection).get(record.status, record.status)
            date_str = record.start_time.strftime('%Y-%m-%d %H:%M') if record.start_time else 'Unknown'
            
            record.display_name = f'{account_name} - {sync_type} ({status}) - {date_str}'
    
    def action_view_details(self):
        """View sync log details"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sync Log Details'),
            'res_model': 'gmail.sync.log',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
    
    def action_retry_sync(self):
        """Retry failed sync"""
        self.ensure_one()
        
        if self.status not in ['failed', 'partial']:
            raise UserError(_('Only failed or partial syncs can be retried'))
        
        # Create new sync log entry
        new_sync = self.create({
            'account_id': self.account_id.id,
            'sync_type': 'manual',
            'start_time': fields.Datetime.now(),
        })
        
        # Start sync process
        try:
            self.account_id._sync_emails()
            new_sync.write({
                'status': 'completed',
                'end_time': fields.Datetime.now(),
            })
        except Exception as e:
            new_sync.write({
                'status': 'failed',
                'end_time': fields.Datetime.now(),
                'error_message': str(e),
            })
            raise
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Retried'),
                'message': _('Sync has been retried successfully'),
                'type': 'success',
            }
        }
    
    @api.model
    def create_sync_log(self, account_id, sync_type='manual'):
        """Create a new sync log entry"""
        return self.create({
            'account_id': account_id,
            'sync_type': sync_type,
            'start_time': fields.Datetime.now(),
        })
    
    def log_success(self, messages_processed=0, messages_created=0, messages_updated=0, api_calls=0, quota_used=0):
        """Mark sync as successful"""
        self.ensure_one()
        self.write({
            'status': 'completed',
            'end_time': fields.Datetime.now(),
            'messages_processed': messages_processed,
            'messages_created': messages_created,
            'messages_updated': messages_updated,
            'api_calls_made': api_calls,
            'quota_used': quota_used,
        })
    
    def log_failure(self, error_message, error_details=None):
        """Mark sync as failed"""
        self.ensure_one()
        self.write({
            'status': 'failed',
            'end_time': fields.Datetime.now(),
            'error_message': error_message,
            'error_details': error_details,
        })
    
    def log_partial_success(self, messages_processed=0, messages_created=0, messages_updated=0, 
                           messages_failed=0, error_message=None):
        """Mark sync as partially successful"""
        self.ensure_one()
        self.write({
            'status': 'partial',
            'end_time': fields.Datetime.now(),
            'messages_processed': messages_processed,
            'messages_created': messages_created,
            'messages_updated': messages_updated,
            'messages_failed': messages_failed,
            'error_message': error_message,
        })
    
    def update_progress(self, messages_processed=None, api_calls=None, quota_used=None):
        """Update sync progress"""
        self.ensure_one()
        update_vals = {}
        
        if messages_processed is not None:
            update_vals['messages_processed'] = messages_processed
        if api_calls is not None:
            update_vals['api_calls_made'] = api_calls
        if quota_used is not None:
            update_vals['quota_used'] = quota_used
        
        if update_vals:
            self.write(update_vals)
    
    @api.model
    def cleanup_old_logs(self, days=30):
        """Clean up old sync logs"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_logs = self.search([
            ('start_time', '<', cutoff_date),
            ('status', 'in', ['completed', 'failed', 'cancelled'])
        ])
        
        _logger.info(f'Cleaning up {len(old_logs)} old sync logs')
        old_logs.unlink()
        
        return len(old_logs)
    
    @api.model
    def get_sync_statistics(self, account_id=None, days=7):
        """Get sync statistics for dashboard"""
        domain = [
            ('start_time', '>=', fields.Datetime.now() - timedelta(days=days))
        ]
        
        if account_id:
            domain.append(('account_id', '=', account_id))
        
        logs = self.search(domain)
        
        stats = {
            'total_syncs': len(logs),
            'successful_syncs': len(logs.filtered(lambda l: l.status == 'completed')),
            'failed_syncs': len(logs.filtered(lambda l: l.status == 'failed')),
            'partial_syncs': len(logs.filtered(lambda l: l.status == 'partial')),
            'total_messages_processed': sum(logs.mapped('messages_processed')),
            'total_messages_created': sum(logs.mapped('messages_created')),
            'total_api_calls': sum(logs.mapped('api_calls_made')),
            'total_quota_used': sum(logs.mapped('quota_used')),
        }
        
        # Calculate success rate
        if stats['total_syncs'] > 0:
            stats['success_rate'] = (stats['successful_syncs'] / stats['total_syncs']) * 100
        else:
            stats['success_rate'] = 0
        
        # Average duration
        completed_logs = logs.filtered(lambda l: l.status in ['completed', 'failed'] and l.duration > 0)
        if completed_logs:
            stats['average_duration'] = sum(completed_logs.mapped('duration')) / len(completed_logs)
        else:
            stats['average_duration'] = 0
        
        return stats
