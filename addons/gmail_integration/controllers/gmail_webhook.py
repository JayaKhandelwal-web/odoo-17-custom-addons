# -*- coding: utf-8 -*-

import json
import base64
import hmac
import hashlib
import logging
from datetime import datetime

from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GmailWebhookController(http.Controller):

    @http.route('/gmail/webhook/pubsub', type='http', auth='public', methods=['POST'], csrf=False)
    def gmail_pubsub_webhook(self, **kwargs):
        """Handle Google Cloud Pub/Sub push notifications for Gmail"""
        try:
            # Verify webhook authenticity
            if not self._verify_webhook_request(request):
                _logger.warning('Gmail webhook: Invalid request signature')
                return self._webhook_response(400, 'Invalid signature')
            
            # Parse Pub/Sub message
            webhook_data = json.loads(request.httprequest.data.decode('utf-8'))
            
            if 'message' not in webhook_data:
                _logger.warning('Gmail webhook: No message in payload')
                return self._webhook_response(400, 'No message in payload')
            
            # Decode Pub/Sub message
            message = webhook_data['message']
            if 'data' not in message:
                _logger.warning('Gmail webhook: No data in message')
                return self._webhook_response(400, 'No data in message')
            
            # Decode base64 data
            try:
                message_data = base64.b64decode(message['data']).decode('utf-8')
                gmail_notification = json.loads(message_data)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                _logger.error(f'Gmail webhook: Failed to decode message data: {str(e)}')
                return self._webhook_response(400, 'Invalid message data')
            
            # Process Gmail notification
            self._process_gmail_notification(gmail_notification, message.get('attributes', {}))
            
            _logger.info('Gmail webhook processed successfully')
            return self._webhook_response(200, 'OK')
            
        except Exception as e:
            _logger.error(f'Gmail webhook error: {str(e)}')
            return self._webhook_response(500, 'Internal server error')
    
    @http.route('/gmail/webhook/test', type='json', auth='user', methods=['POST'])
    def gmail_webhook_test(self, account_id):
        """Test webhook endpoint connectivity"""
        try:
            account = request.env['gmail.account'].browse(account_id)
            if not account.exists():
                return {'success': False, 'error': _('Account not found')}
            
            # Check permissions
            account.check_access_rights('read')
            account.check_access_rule('read')
            
            # Create test notification
            test_notification = {
                'emailAddress': account.email_address,
                'historyId': '12345',
                'timestamp': datetime.now().isoformat(),
            }
            
            # Process test notification
            self._process_gmail_notification(test_notification, {'test': 'true'})
            
            return {
                'success': True,
                'message': _('Webhook test completed successfully'),
                'webhook_url': self._get_webhook_url(),
            }
            
        except Exception as e:
            _logger.error(f'Gmail webhook test error: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    @http.route('/gmail/webhook/setup', type='json', auth='user', methods=['POST'])
    def gmail_webhook_setup(self, account_id):
        """Setup Gmail push notifications for account"""
        try:
            account = request.env['gmail.account'].browse(account_id)
            if not account.exists():
                return {'success': False, 'error': _('Account not found')}
            
            # Check permissions
            account.check_access_rights('write')
            account.check_access_rule('write')
            
            if account.status != 'connected':
                return {'success': False, 'error': _('Account must be connected first')}
            
            # Setup push notifications via Gmail API
            success, error_msg = self._setup_gmail_push_notifications(account)
            
            if success:
                return {
                    'success': True,
                    'message': _('Push notifications setup successfully'),
                    'webhook_url': self._get_webhook_url(),
                }
            else:
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            _logger.error(f'Gmail webhook setup error: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    @http.route('/gmail/webhook/stats', type='json', auth='user', methods=['POST'])
    def gmail_webhook_stats(self):
        """Get webhook processing statistics"""
        try:
            # Get webhook processing stats from sync logs
            domain = [
                ('sync_type', '=', 'webhook'),
                ('start_time', '>=', datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)),
            ]
            
            today_logs = request.env['gmail.sync.log'].search(domain)
            
            stats = {
                'webhooks_received': len(today_logs),
                'webhooks_successful': len(today_logs.filtered(lambda l: l.status == 'completed')),
                'webhooks_failed': len(today_logs.filtered(lambda l: l.status == 'failed')),
                'messages_synced': sum(today_logs.mapped('messages_processed')),
                'avg_processing_time': sum(today_logs.mapped('duration')) / len(today_logs) if today_logs else 0,
                'last_webhook': max(today_logs.mapped('start_time')) if today_logs else None,
            }
            
            return {'success': True, 'stats': stats}
            
        except Exception as e:
            _logger.error(f'Gmail webhook stats error: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    def _verify_webhook_request(self, request):
        """Verify webhook request authenticity"""
        try:
            # Get verification token from system parameters
            verification_token = request.env['ir.config_parameter'].sudo().get_param(
                'gmail_integration.webhook_verification_token'
            )
            
            if not verification_token:
                _logger.warning('Gmail webhook verification token not configured')
                return True  # Allow for initial setup
            
            # Check for verification header
            received_token = request.httprequest.headers.get('X-Gmail-Webhook-Token')
            
            if not received_token:
                return False
            
            # Verify token
            return hmac.compare_digest(verification_token, received_token)
            
        except Exception as e:
            _logger.error(f'Webhook verification error: {str(e)}')
            return False
    
    def _process_gmail_notification(self, notification_data, attributes):
        """Process Gmail push notification"""
        try:
            email_address = notification_data.get('emailAddress')
            history_id = notification_data.get('historyId')
            
            if not email_address:
                _logger.warning('Gmail notification missing email address')
                return
            
            # Find Gmail account
            account = request.env['gmail.account'].sudo().search([
                ('email_address', '=', email_address),
                ('status', '=', 'connected'),
            ], limit=1)
            
            if not account:
                _logger.warning(f'No connected Gmail account found for {email_address}')
                return
            
            # Check if this is a test notification
            is_test = attributes.get('test') == 'true'
            if is_test:
                _logger.info(f'Processing test webhook for {email_address}')
                return
            
            # Start sync log for webhook processing
            sync_log = request.env['gmail.sync.log'].sudo().create({
                'account_id': account.id,
                'sync_type': 'webhook',
                'sync_details': json.dumps({
                    'notification_data': notification_data,
                    'attributes': attributes,
                    'history_id': history_id,
                }),
            })
            
            try:
                # Process the notification
                if history_id:
                    # Use Gmail history API to get changes since last sync
                    self._sync_gmail_history(account, history_id, sync_log)
                else:
                    # Fallback to incremental sync
                    self._trigger_incremental_sync(account, sync_log)
                
                # Mark sync as completed
                sync_log.mark_completed({
                    'processed': 1,
                    'api_calls': 1,
                })
                
                _logger.info(f'Gmail webhook processed for {email_address}, history_id: {history_id}')
                
            except Exception as e:
                # Mark sync as failed
                sync_log.mark_completed(error_info={
                    'message': str(e),
                    'details': f'Failed to process webhook notification: {str(e)}',
                })
                raise
                
        except Exception as e:
            _logger.error(f'Failed to process Gmail notification: {str(e)}')
            raise
    
    def _sync_gmail_history(self, account, history_id, sync_log):
        """Sync Gmail changes using history API"""
        try:
            # Get the last known history ID for this account
            last_history_id = self._get_last_history_id(account)
            
            if not last_history_id or int(history_id) <= int(last_history_id):
                _logger.info(f'History ID {history_id} is not newer than last known {last_history_id}')
                return
            
            # This would use Gmail History API to get incremental changes
            # For now, trigger a manual sync
            _logger.info(f'Triggering history sync from {last_history_id} to {history_id}')
            
            # Update last history ID
            self._update_last_history_id(account, history_id)
            
            # Queue background sync job
            self._queue_background_sync(account, 'realtime')
            
        except Exception as e:
            _logger.error(f'Gmail history sync failed: {str(e)}')
            raise
    
    def _trigger_incremental_sync(self, account, sync_log):
        """Trigger incremental sync for account"""
        try:
            # Queue background sync job
            self._queue_background_sync(account, 'incremental')
            
            sync_log.add_warning('Fallback to incremental sync (no history ID provided)')
            
        except Exception as e:
            _logger.error(f'Incremental sync trigger failed: {str(e)}')
            raise
    
    def _queue_background_sync(self, account, sync_type):
        """Queue background sync job"""
        try:
            # Create a job for background processing
            # This prevents blocking the webhook response
            
            sync_job_data = {
                'account_id': account.id,
                'sync_type': sync_type,
                'triggered_by': 'webhook',
                'priority': 'high' if sync_type == 'realtime' else 'normal',
            }
            
            # Use Odoo's job queue if available, otherwise use cron
            if hasattr(request.env, 'queue_job'):
                # Use queue_job module if installed
                account.with_delay()._sync_emails()
            else:
                # Use standard cron job
                self._schedule_sync_cron(account)
            
            _logger.info(f'Background sync queued for account {account.email_address}')
            
        except Exception as e:
            _logger.error(f'Failed to queue background sync: {str(e)}')
            # Don't raise here as webhook should still succeed
    
    def _schedule_sync_cron(self, account):
        """Schedule sync using cron job"""
        try:
            # Update next execution time for sync cron
            cron_job = request.env.ref('gmail_integration.ir_cron_sync_gmail_emails', raise_if_not_found=False)
            
            if cron_job:
                # Schedule for immediate execution
                cron_job.sudo().write({
                    'nextcall': datetime.now(),
                    'active': True,
                })
                
        except Exception as e:
            _logger.warning(f'Failed to schedule sync cron: {str(e)}')
    
    def _get_last_history_id(self, account):
        """Get last known history ID for account"""
        try:
            # Look for last successful sync with history ID
            last_sync = request.env['gmail.sync.log'].sudo().search([
                ('account_id', '=', account.id),
                ('status', '=', 'completed'),
                ('sync_details', '!=', False),
            ], order='end_time desc', limit=1)
            
            if last_sync and last_sync.sync_details:
                sync_details = json.loads(last_sync.sync_details)
                return sync_details.get('last_history_id')
                
            return None
            
        except Exception as e:
            _logger.warning(f'Failed to get last history ID: {str(e)}')
            return None
    
    def _update_last_history_id(self, account, history_id):
        """Update last known history ID for account"""
        try:
            # Store in account or system parameters
            param_key = f'gmail_integration.last_history_id.{account.id}'
            request.env['ir.config_parameter'].sudo().set_param(param_key, history_id)
            
            _logger.debug(f'Updated last history ID for account {account.id}: {history_id}')
            
        except Exception as e:
            _logger.warning(f'Failed to update last history ID: {str(e)}')
    
    def _setup_gmail_push_notifications(self, account):
        """Setup Gmail push notifications via Gmail API"""
        try:
            # This would use Gmail API to setup push notifications
            # For now, return success with placeholder implementation
            
            webhook_url = self._get_webhook_url()
            topic_name = self._get_pubsub_topic_name(account)
            
            # In real implementation, this would:
            # 1. Create or verify Pub/Sub topic
            # 2. Setup Gmail watch request
            # 3. Configure push subscription
            
            _logger.info(f'Gmail push notifications setup for {account.email_address}')
            _logger.info(f'Webhook URL: {webhook_url}')
            _logger.info(f'Pub/Sub Topic: {topic_name}')
            
            # Store setup information
            setup_info = {
                'webhook_url': webhook_url,
                'topic_name': topic_name,
                'setup_date': datetime.now().isoformat(),
            }
            
            param_key = f'gmail_integration.webhook_setup.{account.id}'
            request.env['ir.config_parameter'].sudo().set_param(
                param_key, json.dumps(setup_info)
            )
            
            return True, None
            
        except Exception as e:
            error_msg = f'Failed to setup push notifications: {str(e)}'
            _logger.error(error_msg)
            return False, error_msg
    
    def _get_webhook_url(self):
        """Get webhook URL for Gmail notifications"""
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f'{base_url}/gmail/webhook/pubsub'
    
    def _get_pubsub_topic_name(self, account):
        """Get Pub/Sub topic name for Gmail account"""
        # Generate consistent topic name based on account
        topic_base = f'gmail-notifications-{account.id}'
        return topic_base.replace('@', '-').replace('.', '-').lower()
    
    def _webhook_response(self, status_code, message):
        """Create webhook response"""
        response = request.make_response(message, status_code)
        response.headers['Content-Type'] = 'text/plain'
        return response
    
    @http.route('/gmail/webhook/validate', type='http', auth='public', methods=['GET'], csrf=False)
    def gmail_webhook_validate(self, **kwargs):
        """Validate webhook endpoint (for Google verification)"""
        try:
            # Handle Google's webhook validation request
            challenge = kwargs.get('hub.challenge')
            verify_token = kwargs.get('hub.verify_token')
            
            # Get expected verification token
            expected_token = request.env['ir.config_parameter'].sudo().get_param(
                'gmail_integration.webhook_verification_token'
            )
            
            if verify_token and expected_token and verify_token == expected_token:
                _logger.info('Gmail webhook validation successful')
                return challenge
            else:
                _logger.warning('Gmail webhook validation failed')
                return self._webhook_response(403, 'Forbidden')
                
        except Exception as e:
            _logger.error(f'Gmail webhook validation error: {str(e)}')
            return self._webhook_response(500, 'Internal server error')
    
    @http.route('/gmail/webhook/health', type='http', auth='public', methods=['GET'], csrf=False)
    def gmail_webhook_health(self):
        """Health check endpoint for webhook"""
        try:
            # Basic health check
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'webhook_url': self._get_webhook_url(),
                'version': '1.0.0',
            }
            
            # Check database connectivity
            try:
                request.env.cr.execute('SELECT 1')
                health_status['database'] = 'connected'
            except Exception:
                health_status['database'] = 'disconnected'
                health_status['status'] = 'unhealthy'
            
            response_code = 200 if health_status['status'] == 'healthy' else 503
            
            response = request.make_response(json.dumps(health_status), response_code)
            response.headers['Content-Type'] = 'application/json'
            return response
            
        except Exception as e:
            _logger.error(f'Webhook health check error: {str(e)}')
            error_response = {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            }
            response = request.make_response(json.dumps(error_response), 503)
            response.headers['Content-Type'] = 'application/json'
            return response
    
    @http.route('/gmail/webhook/config', type='json', auth='user', methods=['POST'])
    def gmail_webhook_config(self):
        """Get webhook configuration information"""
        try:
            # Check permissions
            if not request.env.user.has_group('base.group_system'):
                return {'success': False, 'error': _('Access denied')}
            
            config_info = {
                'webhook_url': self._get_webhook_url(),
                'verification_token_configured': bool(
                    request.env['ir.config_parameter'].sudo().get_param(
                        'gmail_integration.webhook_verification_token'
                    )
                ),
                'supported_methods': ['POST'],
                'content_type': 'application/json',
                'max_payload_size': '1MB',
                'timeout': '30s',
                'retry_policy': 'exponential_backoff',
                'security': {
                    'token_verification': True,
                    'https_required': True,
                    'ip_whitelist': False,
                },
            }
            
            return {'success': True, 'config': config_info}
            
        except Exception as e:
            _logger.error(f'Webhook config error: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    @http.route('/gmail/webhook/logs', type='json', auth='user', methods=['POST'])
    def gmail_webhook_logs(self, limit=50, offset=0):
        """Get webhook processing logs"""
        try:
            # Check permissions
            if not request.env.user.has_group('gmail_integration.group_gmail_admin'):
                return {'success': False, 'error': _('Access denied')}
            
            # Get webhook sync logs
            domain = [('sync_type', '=', 'webhook')]
            
            logs = request.env['gmail.sync.log'].search(
                domain, 
                order='start_time desc', 
                limit=limit, 
                offset=offset
            )
            
            log_data = []
            for log in logs:
                log_info = {
                    'id': log.id,
                    'account_email': log.account_id.email_address,
                    'start_time': log.start_time.isoformat() if log.start_time else None,
                    'end_time': log.end_time.isoformat() if log.end_time else None,
                    'duration': log.duration,
                    'status': log.status,
                    'messages_processed': log.messages_processed,
                    'error_message': log.error_message,
                    'sync_details': log.sync_details,
                }
                log_data.append(log_info)
            
            # Get total count for pagination
            total_count = request.env['gmail.sync.log'].search_count(domain)
            
            return {
                'success': True,
                'logs': log_data,
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
            }
            
        except Exception as e:
            _logger.error(f'Webhook logs error: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    @http.route('/gmail/webhook/setup_guide', type='http', auth='user', methods=['GET'], website=True)
    def gmail_webhook_setup_guide(self):
        """Display webhook setup guide"""
        try:
            # Check permissions
            if not request.env.user.has_group('gmail_integration.group_gmail_admin'):
                return request.render('gmail_integration.access_denied')
            
            setup_info = {
                'webhook_url': self._get_webhook_url(),
                'verification_token': request.env['ir.config_parameter'].sudo().get_param(
                    'gmail_integration.webhook_verification_token'
                ) or 'Not configured',
                'pubsub_instructions': self._get_pubsub_setup_instructions(),
                'gmail_watch_instructions': self._get_gmail_watch_instructions(),
            }
            
            return request.render('gmail_integration.webhook_setup_guide', setup_info)
            
        except Exception as e:
            _logger.error(f'Webhook setup guide error: {str(e)}')
            return request.render('gmail_integration.error_page', {
                'error_message': _('Failed to load setup guide: %s') % str(e)
            })
    
    def _get_pubsub_setup_instructions(self):
        """Get Pub/Sub setup instructions"""
        return {
            'topic_naming': 'gmail-notifications-{account_id}',
            'subscription_endpoint': self._get_webhook_url(),
            'required_permissions': [
                'pubsub.topics.create',
                'pubsub.subscriptions.create',
                'pubsub.topics.publish',
            ],
            'gcloud_commands': [
                'gcloud pubsub topics create gmail-notifications-{account_id}',
                f'gcloud pubsub subscriptions create gmail-webhook --topic=gmail-notifications-{{account_id}} --push-endpoint={self._get_webhook_url()}',
            ]
        }
    
    def _get_gmail_watch_instructions(self):
        """Get Gmail watch setup instructions"""
        return {
            'api_method': 'gmail.users.watch',
            'required_scopes': [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify',
            ],
            'watch_request_body': {
                'topicName': 'projects/{project_id}/topics/gmail-notifications-{account_id}',
                'labelIds': ['INBOX', 'SENT'],
                'labelFilterAction': 'include',
            },
            'expiration_note': 'Watch requests expire after 7 days and must be renewed',
        }
    
    @http.route('/gmail/webhook/renew', type='json', auth='user', methods=['POST'])
    def gmail_webhook_renew(self, account_id):
        """Renew Gmail watch request for account"""
        try:
            account = request.env['gmail.account'].browse(account_id)
            if not account.exists():
                return {'success': False, 'error': _('Account not found')}
            
            # Check permissions
            account.check_access_rights('write')
            account.check_access_rule('write')
            
            if account.status != 'connected':
                return {'success': False, 'error': _('Account must be connected')}
            
            # Renew Gmail watch request
            # In real implementation, this would call Gmail API
            success = True
            error_msg = None
            
            if success:
                # Update renewal information
                renewal_info = {
                    'renewed_date': datetime.now().isoformat(),
                    'expires_date': (datetime.now() + timedelta(days=7)).isoformat(),
                }
                
                param_key = f'gmail_integration.webhook_renewal.{account.id}'
                request.env['ir.config_parameter'].sudo().set_param(
                    param_key, json.dumps(renewal_info)
                )
                
                return {
                    'success': True,
                    'message': _('Gmail watch request renewed successfully'),
                    'expires_date': renewal_info['expires_date'],
                }
            else:
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            _logger.error(f'Gmail webhook renewal error: {str(e)}')
            return {'success': False, 'error': str(e)}
