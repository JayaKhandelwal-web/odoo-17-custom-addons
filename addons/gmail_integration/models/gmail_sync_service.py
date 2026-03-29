# -*- coding: utf-8 -*-

import json
import logging
import base64
from datetime import datetime
from email.utils import parsedate_to_datetime

from odoo import models, api
from odoo.exceptions import UserError

try:
    from googleapiclient.errors import HttpError
except ImportError:
    logging.getLogger(__name__).warning('Google API libraries not found')

_logger = logging.getLogger(__name__)


class GmailSyncService(models.TransientModel):
    _name = 'gmail.sync.service'
    _description = 'Gmail Synchronization Service'

    def sync_account_emails(self, account_id):
        """Sync emails for a specific Gmail account"""
        account = self.env['gmail.account'].browse(account_id)
        
        if account.status != 'connected':
            raise UserError(f'Account {account.email_address} is not connected')
        
        try:
            # Create sync log using your existing method
            sync_log = self.env['gmail.sync.log'].create_sync_log(
                account.id, 
                'full' if not account.history_id else 'incremental'
            )
            
            service = account._get_gmail_service()
            messages_processed = 0
            messages_created = 0
            messages_updated = 0
            
            # Get list of messages
            if account.history_id:
                # Incremental sync using history
                messages_processed, messages_created, messages_updated = self._sync_incremental(
                    account, service, sync_log
                )
            else:
                # Full sync (limited to 1 day)
                messages_processed, messages_created, messages_updated = self._sync_full(
                    account, service, sync_log
                )
            
            # Update sync log using your existing methods
            sync_log.log_success(
                messages_processed=messages_processed,
                messages_created=messages_created,
                messages_updated=messages_updated,
                api_calls=0,  # You can track this if needed
                quota_used=0  # You can track this if needed
            )
            
            # Update account last sync
            account.last_sync_date = datetime.now()
            
            _logger.info(f'Sync completed for {account.email_address}: {messages_processed} messages processed')
            
        except Exception as e:
            _logger.error(f'Sync failed for {account.email_address}: {e}')
            if 'sync_log' in locals():
                sync_log.log_failure(str(e))
            raise

    def _sync_full(self, account, service, sync_log):
        """Perform limited initial email synchronization (1 day only)"""
        messages_processed = 0
        messages_created = 0
        messages_updated = 0
        
        try:
            # Get labels to sync
            labels_to_sync = self._get_labels_to_sync(account)
            
            # Calculate date for 1 day ago
            from datetime import datetime, timedelta
            one_day_ago = datetime.now() - timedelta(days=1)
            query_date = one_day_ago.strftime('%Y/%m/%d')
            
            _logger.info(f'Starting limited sync for {account.email_address} from {query_date}')
            
            for label in labels_to_sync:
                _logger.info(f'Syncing label {label} for {account.email_address} from {query_date}')
                
                # Get messages for this label from the last 1 day only
                result = service.users().messages().list(
                    userId='me',
                    labelIds=[label],
                    q=f'after:{query_date}',  # Only messages from 1 day ago
                    maxResults=100  # Process in batches
                ).execute()
                
                messages = result.get('messages', [])
                _logger.info(f'Found {len(messages)} messages in {label} from last 1 day')
                
                for message_ref in messages:
                    try:
                        # Get full message details - FIXED: removed duplicate userId
                        message = service.users().messages().get(
                            userId='me',
                            id=message_ref['id'],
                            format='full'
                        ).execute()
                        
                        # Process message
                        processed = self._process_gmail_message(account, message)
                        if processed == 'created':
                            messages_created += 1
                        elif processed == 'updated':
                            messages_updated += 1
                        
                        messages_processed += 1
                        
                        # Update sync log progress periodically
                        if messages_processed % 10 == 0:
                            sync_log.update_progress(messages_processed=messages_processed)
                            
                    except Exception as e:
                        _logger.error(f'Failed to process message {message_ref["id"]}: {e}')
                        continue
                
                # Handle pagination for recent messages only
                while 'nextPageToken' in result:
                    result = service.users().messages().list(
                        userId='me',
                        labelIds=[label],
                        q=f'after:{query_date}',
                        maxResults=100,
                        pageToken=result['nextPageToken']
                    ).execute()
                    
                    messages = result.get('messages', [])
                    for message_ref in messages:
                        try:
                            # FIXED: removed duplicate userId
                            message = service.users().messages().get(
                                userId='me',
                                id=message_ref['id'],
                                format='full'
                            ).execute()
                            
                            processed = self._process_gmail_message(account, message)
                            if processed == 'created':
                                messages_created += 1
                            elif processed == 'updated':
                                messages_updated += 1
                            
                            messages_processed += 1
                            
                        except Exception as e:
                            _logger.error(f'Failed to process message {message_ref["id"]}: {e}')
                            continue
            
            # Update history ID for future incremental syncs
            profile = service.users().getProfile(userId='me').execute()
            account.history_id = profile.get('historyId')
            
            _logger.info(f'Limited sync completed for {account.email_address}: {messages_processed} recent messages processed')
            
        except Exception as e:
            _logger.error(f'Limited sync error for {account.email_address}: {e}')
            raise
        
        return messages_processed, messages_created, messages_updated

    def _sync_incremental(self, account, service, sync_log):
        """Perform incremental email synchronization using history"""
        messages_processed = 0
        messages_created = 0
        messages_updated = 0
        
        try:
            # Get history since last sync
            history = service.users().history().list(
                userId='me',
                startHistoryId=account.history_id,
                labelId='INBOX'  # Focus on inbox for incremental
            ).execute()
            
            if 'history' not in history:
                _logger.info(f'No new history for {account.email_address}')
                return messages_processed, messages_created, messages_updated
            
            for history_record in history['history']:
                # Process added messages
                if 'messagesAdded' in history_record:
                    for added_message in history_record['messagesAdded']:
                        try:
                            message = service.users().messages().get(
                                userId='me',
                                id=added_message['message']['id'],
                                format='full'
                            ).execute()
                            
                            processed = self._process_gmail_message(account, message)
                            if processed == 'created':
                                messages_created += 1
                            elif processed == 'updated':
                                messages_updated += 1
                            
                            messages_processed += 1
                            
                        except Exception as e:
                            _logger.error(f'Failed to process added message: {e}')
                            continue
                
                # Process deleted messages
                if 'messagesDeleted' in history_record:
                    for deleted_message in history_record['messagesDeleted']:
                        try:
                            self._handle_deleted_message(account, deleted_message['message']['id'])
                        except Exception as e:
                            _logger.error(f'Failed to process deleted message: {e}')
                            continue
            
            # Update history ID
            account.history_id = history.get('historyId')
            
        except HttpError as e:
            if e.resp.status == 404:
                _logger.warning(f'History ID expired for {account.email_address}, performing full sync')
                return self._sync_full(account, service, sync_log)
            else:
                raise
        
        return messages_processed, messages_created, messages_updated

    def _process_gmail_message(self, account, gmail_message):
        """Process a single Gmail message"""
        gmail_id = gmail_message['id']
        
        # Check if message already exists
        existing_message = self.env['gmail.message'].search([
            ('gmail_message_id', '=', gmail_id),
            ('account_id', '=', account.id)
        ], limit=1)
        
        # Extract message data
        message_data = self._extract_message_data(gmail_message, account)
        message_data['account_id'] = account.id
        message_data['gmail_message_id'] = gmail_id
        
        if existing_message:
            # Update existing message
            existing_message.write(message_data)
            return 'updated'
        else:
            # Create new message
            self.env['gmail.message'].create(message_data)
            return 'created'

    def _extract_message_data(self, gmail_message, account):
        """Extract data from Gmail message for Odoo storage"""
        payload = gmail_message.get('payload', {})
        headers = payload.get('headers', [])
        
        # Extract headers
        header_dict = {h['name'].lower(): h['value'] for h in headers}
        
        # Extract basic info
        subject = header_dict.get('subject', 'No Subject')
        from_email = header_dict.get('from', '')
        to_emails = header_dict.get('to', '')
        cc_emails = header_dict.get('cc', '')
        bcc_emails = header_dict.get('bcc', '')
        date_str = header_dict.get('date', '')
        
        # Parse date
        message_date = datetime.now()
        if date_str:
            try:
                message_date = parsedate_to_datetime(date_str)
            except:
                pass
        
        # Extract body
        body_html, body_plain = self._extract_message_body(payload)
        
        # Extract snippet
        snippet = gmail_message.get('snippet', '')
        
        # Determine direction
        direction = 'inbound'  # Default
        if from_email and account.email_address in from_email:
            if 'SENT' in gmail_message.get('labelIds', []):
                direction = 'outbound'
            elif 'DRAFT' in gmail_message.get('labelIds', []):
                direction = 'draft'
        
        # Extract other properties
        is_read = 'UNREAD' not in gmail_message.get('labelIds', [])
        is_starred = 'STARRED' in gmail_message.get('labelIds', [])
        is_important = 'IMPORTANT' in gmail_message.get('labelIds', [])
        
        return {
            'subject': subject,
            'from_email': from_email,
            'from_name': self._extract_name_from_email(from_email),
            'to_emails': to_emails,
            'cc_emails': cc_emails,
            'bcc_emails': bcc_emails,
            'date': message_date,
            'body_html': body_html,
            'body_plain': body_plain,
            'snippet': snippet,
            'direction': direction,
            'is_read': is_read,
            'is_starred': is_starred,
            'is_important': is_important,
            'gmail_labels': ','.join(gmail_message.get('labelIds', [])),
            'message_size': gmail_message.get('sizeEstimate', 0),
            'sync_date': datetime.now(),
            'sync_status': 'synced'
        }

    def _extract_message_body(self, payload):
        """Extract HTML and plain text body from message payload"""
        body_html = ''
        body_plain = ''
        
        def extract_body_recursive(part):
            nonlocal body_html, body_plain
            
            if 'parts' in part:
                for subpart in part['parts']:
                    extract_body_recursive(subpart)
            else:
                mime_type = part.get('mimeType', '')
                body = part.get('body', {})
                data = body.get('data', '')
                
                if data:
                    try:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8')
                        if mime_type == 'text/html':
                            body_html = decoded
                        elif mime_type == 'text/plain':
                            body_plain = decoded
                    except:
                        pass
        
        extract_body_recursive(payload)
        return body_html, body_plain

    def _extract_name_from_email(self, email_string):
        """Extract name from email string like 'John Doe <john@example.com>'"""
        if '<' in email_string and '>' in email_string:
            return email_string.split('<')[0].strip().strip('"')
        return ''

    def _handle_deleted_message(self, account, gmail_id):
        """Handle deleted Gmail message"""
        message = self.env['gmail.message'].search([
            ('gmail_message_id', '=', gmail_id),
            ('account_id', '=', account.id)
        ], limit=1)
        
        if message:
            # Mark as deleted instead of actually deleting
            message.write({
                'sync_status': 'deleted',
                'last_updated': datetime.now()
            })

    def _get_labels_to_sync(self, account):
        """Get list of Gmail labels to sync based on account settings"""
        labels = []
        
        if account.sync_inbox:
            labels.append('INBOX')
        if account.sync_sent:
            labels.append('SENT')
        if account.sync_drafts:
            labels.append('DRAFT')
        if account.sync_spam:
            labels.append('SPAM')
        if account.sync_trash:
            labels.append('TRASH')
        
        return labels

    @api.model
    def process_pubsub_notification(self, account_id, history_id):
        """Process Pub/Sub notification for incremental sync"""
        account = self.env['gmail.account'].browse(account_id)
        
        if account.status != 'connected':
            return
        
        try:
            # Create sync log for notification using your existing method
            sync_log = self.env['gmail.sync.log'].create_sync_log(
                account.id, 
                'realtime'
            )
            
            # Update account history ID and sync
            old_history_id = account.history_id
            account.history_id = history_id
            
            service = account._get_gmail_service()
            messages_processed, messages_created, messages_updated = self._sync_incremental(
                account, service, sync_log
            )
            
            # Use your existing log success method
            sync_log.log_success(
                messages_processed=messages_processed,
                messages_created=messages_created,
                messages_updated=messages_updated
            )
            
            _logger.info(f'Notification sync completed for {account.email_address}')
            
        except Exception as e:
            _logger.error(f'Notification sync failed for {account.email_address}: {e}')
            if 'sync_log' in locals():
                sync_log.log_failure(str(e))
            raise
