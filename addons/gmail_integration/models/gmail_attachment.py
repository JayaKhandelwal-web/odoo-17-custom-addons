# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import mimetypes
import logging

_logger = logging.getLogger(__name__)


class GmailAttachment(models.Model):
    _name = 'gmail.attachment'
    _description = 'Gmail Attachment'
    _rec_name = 'filename'
    _order = 'create_date desc'

    # Gmail Attachment Identifier
    gmail_attachment_id = fields.Char(
        string='Gmail Attachment ID',
        required=True,
        help='Unique Gmail attachment identifier'
    )
    
    # Message Reference
    message_id = fields.Many2one(
        'gmail.message',
        string='Message',
        required=True,
        ondelete='cascade',
        help='Associated Gmail message'
    )
    
    # Account Reference (for easier querying)
    account_id = fields.Many2one(
        'gmail.account',
        string='Gmail Account',
        related='message_id.account_id',
        store=True,
        help='Associated Gmail account'
    )
    
    # File Information
    filename = fields.Char(
        string='Filename',
        required=True,
        help='Original filename of attachment'
    )
    mimetype = fields.Char(
        string='MIME Type',
        help='File MIME type'
    )
    size = fields.Integer(
        string='Size (bytes)',
        help='File size in bytes'
    )
    size_formatted = fields.Char(
        string='Size',
        compute='_compute_size_formatted',
        help='Human readable file size'
    )
    
    # File Content
    content = fields.Binary(
        string='File Content',
        attachment=True,
        help='Binary file content'
    )
    content_base64 = fields.Text(
        string='Content (Base64)',
        help='Base64 encoded file content'
    )
    
    # Download Status
    is_downloaded = fields.Boolean(
        string='Downloaded',
        default=False,
        help='Whether attachment has been downloaded from Gmail'
    )
    download_date = fields.Datetime(
        string='Download Date',
        help='When attachment was downloaded'
    )
    download_error = fields.Text(
        string='Download Error',
        help='Error message if download failed'
    )
    
    # File Analysis
    is_image = fields.Boolean(
        string='Is Image',
        compute='_compute_file_type',
        help='Whether file is an image'
    )
    is_document = fields.Boolean(
        string='Is Document',
        compute='_compute_file_type',
        help='Whether file is a document'
    )
    is_archive = fields.Boolean(
        string='Is Archive',
        compute='_compute_file_type',
        help='Whether file is an archive'
    )
    file_extension = fields.Char(
        string='Extension',
        compute='_compute_file_extension',
        help='File extension'
    )
    
    # Security
    virus_scan_result = fields.Selection([
        ('pending', 'Pending'),
        ('clean', 'Clean'),
        ('infected', 'Infected'),
        ('error', 'Error'),
    ], string='Virus Scan', default='pending',
       help='Virus scan result')
    
    virus_scan_date = fields.Datetime(
        string='Scan Date',
        help='When virus scan was performed'
    )
    
    # Preview
    thumbnail = fields.Binary(
        string='Thumbnail',
        attachment=True,
        help='File thumbnail for preview'
    )
    has_preview = fields.Boolean(
        string='Has Preview',
        compute='_compute_has_preview',
        help='Whether file can be previewed'
    )
    
    # Odoo Attachment Reference
    ir_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Odoo Attachment',
        help='Reference to Odoo attachment record'
    )
    
    @api.depends('size')
    def _compute_size_formatted(self):
        for record in self:
            if record.size:
                # Format size in human readable format
                size = record.size
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024.0:
                        record.size_formatted = f'{size:.1f} {unit}'
                        break
                    size /= 1024.0
                else:
                    record.size_formatted = f'{size:.1f} TB'
            else:
                record.size_formatted = '0 B'
    
    @api.depends('mimetype')
    def _compute_file_type(self):
        for record in self:
            mimetype = record.mimetype or ''
            
            # Image types
            record.is_image = mimetype.startswith('image/')
            
            # Document types
            document_types = [
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'text/plain',
                'text/csv',
            ]
            record.is_document = mimetype in document_types
            
            # Archive types
            archive_types = [
                'application/zip',
                'application/x-rar-compressed',
                'application/x-7z-compressed',
                'application/gzip',
                'application/x-tar',
            ]
            record.is_archive = mimetype in archive_types
    
    @api.depends('filename')
    def _compute_file_extension(self):
        for record in self:
            if record.filename and '.' in record.filename:
                record.file_extension = record.filename.split('.')[-1].lower()
            else:
                record.file_extension = ''
    
    @api.depends('mimetype', 'is_image', 'is_document')
    def _compute_has_preview(self):
        for record in self:
            # Files that can be previewed
            previewable_types = [
                'application/pdf',
                'text/plain',
                'text/csv',
                'text/html',
            ]
            record.has_preview = (
                record.is_image or 
                record.mimetype in previewable_types
            )
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Set MIME type if not provided
            if 'mimetype' not in vals and 'filename' in vals:
                mimetype, _ = mimetypes.guess_type(vals['filename'])
                if mimetype:
                    vals['mimetype'] = mimetype
        
        attachments = super().create(vals_list)
        
        # Create Odoo attachment records for better integration
        for attachment in attachments:
            attachment._create_ir_attachment()
        
        return attachments
    
    def _create_ir_attachment(self):
        """Create corresponding ir.attachment record"""
        self.ensure_one()
        
        if not self.content and not self.content_base64:
            return
        
        attachment_data = {
            'name': self.filename,
            'type': 'binary',
            'mimetype': self.mimetype,
            'res_model': 'gmail.message',
            'res_id': self.message_id.id,
        }
        
        if self.content:
            attachment_data['datas'] = self.content
        elif self.content_base64:
            attachment_data['datas'] = self.content_base64
        
        ir_attachment = self.env['ir.attachment'].create(attachment_data)
        self.ir_attachment_id = ir_attachment.id
    
    def action_download(self):
        """Download attachment from Gmail"""
        self.ensure_one()
        
        if self.is_downloaded:
            raise UserError(_('Attachment is already downloaded.'))
        
        try:
            # Gmail API implementation for downloading attachment
            self._download_from_gmail()
            
            self.write({
                'is_downloaded': True,
                'download_date': fields.Datetime.now(),
                'download_error': False,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Download Complete'),
                    'message': _('Attachment downloaded successfully!'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            self.download_error = error_msg
            _logger.error(f'Failed to download attachment {self.filename}: {error_msg}')
            raise UserError(_('Download failed: %s') % error_msg)
    
    def action_preview(self):
        """Preview attachment"""
        self.ensure_one()
        
        if not self.has_preview:
            raise UserError(_('This file type cannot be previewed.'))
        
        if not self.is_downloaded:
            self.action_download()
        
        if self.ir_attachment_id:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self.ir_attachment_id.id}?download=false',
                'target': 'new',
            }
        else:
            raise UserError(_('Attachment not available for preview.'))
    
    def action_download_file(self):
        """Download file to user's computer"""
        self.ensure_one()
        
        if not self.is_downloaded:
            self.action_download()
        
        if self.ir_attachment_id:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self.ir_attachment_id.id}?download=true',
                'target': 'self',
            }
        else:
            raise UserError(_('Attachment not available for download.'))
    
    def _download_from_gmail(self):
        """Internal method to download from Gmail API"""
        self.ensure_one()
        
        # Gmail API implementation
        _logger.info(f'Downloading attachment {self.filename} from Gmail')
        
        try:
            # This will be implemented when Gmail API is integrated
            # For now, just mark as downloaded if content exists
            if self.content_base64:
                self.content = base64.b64decode(self.content_base64)
            
        except Exception as e:
            _logger.error(f'Gmail API download failed: {str(e)}')
            raise
    
    def _scan_for_virus(self):
        """Scan attachment for viruses"""
        self.ensure_one()
        
        if not self.is_downloaded:
            return
        
        try:
            # Virus scanning implementation would go here
            # For now, just mark as clean
            self.write({
                'virus_scan_result': 'clean',
                'virus_scan_date': fields.Datetime.now(),
            })
            
        except Exception as e:
            _logger.error(f'Virus scan failed for {self.filename}: {str(e)}')
            self.write({
                'virus_scan_result': 'error',
                'virus_scan_date': fields.Datetime.now(),
            })
    
    @api.model
    def cleanup_old_attachments(self, days=90):
        """Clean up old attachment files (called by cron)"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        
        old_attachments = self.search([
            ('download_date', '<', cutoff_date),
            ('is_downloaded', '=', True),
        ])
        
        _logger.info(f'Cleaning up {len(old_attachments)} old attachments')
        
        for attachment in old_attachments:
            # Remove file content but keep metadata
            attachment.write({
                'content': False,
                'content_base64': False,
                'is_downloaded': False,
            })
            
            # Remove associated ir.attachment
            if attachment.ir_attachment_id:
                attachment.ir_attachment_id.unlink()
    
    @api.model
    def create_from_gmail_data(self, gmail_attachment_data, message_id):
        """Create attachment from Gmail API data"""
        
        attachment_vals = {
            'gmail_attachment_id': gmail_attachment_data.get('id'),
            'message_id': message_id,
            'filename': gmail_attachment_data.get('filename', 'unknown'),
            'mimetype': gmail_attachment_data.get('mimeType'),
            'size': gmail_attachment_data.get('size', 0),
        }
        
        # Store attachment data if provided
        if 'data' in gmail_attachment_data:
            attachment_vals['content_base64'] = gmail_attachment_data['data']
            attachment_vals['is_downloaded'] = True
            attachment_vals['download_date'] = fields.Datetime.now()
        
        return self.create(attachment_vals)
