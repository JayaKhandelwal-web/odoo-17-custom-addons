# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
import json
import base64
import threading
import time

_logger = logging.getLogger(__name__)


class FleetBooking(models.Model):
    _inherit = 'fleet.booking'

    # WhatsApp Integration Fields
    interakt_message_ids = fields.One2many('interakt.message.log', 'res_id',
                                           domain=[('model_name', '=', 'fleet.booking')],
                                           string='WhatsApp Messages')
    interakt_message_count = fields.Integer(string='WhatsApp Messages',
                                            compute='_compute_interakt_message_count')

    # Confirmation Template Tracking
    confirmation_template_sent = fields.Boolean(string='Confirmation Sent',
                                                default=False, readonly=True)
    confirmation_sent_date = fields.Datetime(string='Confirmation Sent Date',
                                             readonly=True)
    confirmation_message_id = fields.Char(string='Confirmation Message ID',
                                          readonly=True)

    # NEW: Confirmation Receipt Template Tracking
    confirmation_receipt_sent = fields.Boolean(string='Receipt Sent',
                                               default=False, readonly=True)
    confirmation_receipt_sent_date = fields.Datetime(string='Receipt Sent Date',
                                                     readonly=True)
    confirmation_receipt_message_id = fields.Char(string='Receipt Message ID',
                                                  readonly=True)
    confirmation_receipt_pdf_url = fields.Char(string='Receipt PDF URL',
                                               help='Public URL of the confirmation receipt PDF')

    # Quotation Template Tracking
    quotation_template_sent = fields.Boolean(string='Quotation Sent',
                                             default=False, readonly=True)
    quotation_sent_date = fields.Datetime(string='Quotation Sent Date',
                                          readonly=True)
    quotation_message_id = fields.Char(string='Quotation Message ID',
                                       readonly=True)
    quotation_pdf_url = fields.Char(string='Quotation PDF URL',
                                    help='Public URL of the quotation PDF for WhatsApp')

    # Followup Template Tracking
    followup_template_sent = fields.Boolean(string='Followup Sent',
                                            default=False, readonly=True)
    followup_sent_date = fields.Datetime(string='Followup Sent Date',
                                         readonly=True)
    followup_message_id = fields.Char(string='Followup Message ID',
                                      readonly=True)

    @api.depends('interakt_message_ids')
    def _compute_interakt_message_count(self):
        """Compute WhatsApp message count"""
        for booking in self:
            booking.interakt_message_count = len(booking.interakt_message_ids)

    def write(self, vals):
        """Override write to send templates when booking state changes"""
        result = super(FleetBooking, self).write(vals)

        # Check if state changed
        if 'state' in vals:
            for booking in self:
                # Send quotation template when state changes to quotation
                if vals['state'] == 'quotation':
                    booking._send_quotation_template()

                # Send confirmation template when state changes to confirmed
                elif vals['state'] == 'confirmed':
                    booking._send_confirmation_template()

                # Send followup template when state changes to followup
                elif vals['state'] == 'followup':
                    booking._send_followup_template()

        return result

    def _get_confirmation_pdf_url_from_invoice_document(self):
        """
        Get the confirmation receipt PDF URL from fleet.booking.invoice.document model.
        Similar to quotation PDF but for confirmed state.

        Returns:
            str: Public URL to the PDF file or False if not found
        """
        self.ensure_one()

        # Search for the latest confirmed stage invoice document
        invoice_document = self.env['fleet.booking.invoice.document'].sudo().search([
            ('booking_id', '=', self.id),
            ('booking_state', '=', 'confirmed'),
        ], order='create_date desc', limit=1)

        # If no confirmed document exists, try to generate one
        if not invoice_document:
            _logger.info(f"No confirmation receipt PDF found for booking {self.name}, attempting to generate...")
            try:
                invoice_document = self.env['fleet.booking.invoice.document'].sudo().generate_invoice_pdf(
                    booking_id=self.id,
                    booking_state='confirmed'
                )
            except Exception as e:
                _logger.error(f"Failed to generate confirmation receipt PDF for booking {self.name}: {str(e)}")
                return False

        if not invoice_document or not invoice_document.pdf_file:
            _logger.warning(f"No PDF file available in invoice document for booking {self.name}")
            return False

        # Get the ir.attachment ID for the PDF file
        attachment = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'fleet.booking.invoice.document'),
            ('res_id', '=', invoice_document.id),
            ('res_field', '=', 'pdf_file')
        ], limit=1)

        if not attachment:
            _logger.warning(f"No attachment found for invoice document {invoice_document.id}")
            return False

        # Build the public URL using the ATTACHMENT ID
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        pdf_url = "{}/web/content/{}".format(base_url, attachment.id)

        _logger.info(
            f"Generated confirmation receipt PDF URL for booking {self.name}: {pdf_url} (Attachment ID: {attachment.id})")
        return pdf_url

    def _get_quotation_pdf_url_from_invoice_document(self):
        """
        Get the quotation PDF URL from fleet.booking.invoice.document model.
        This uses the archived PDF documents generated by fleet_booking_invoice_archive module.

        Returns:
            str: Public URL to the PDF file or False if not found
        """
        self.ensure_one()

        # Search for the latest quotation stage invoice document
        invoice_document = self.env['fleet.booking.invoice.document'].sudo().search([
            ('booking_id', '=', self.id),
            ('booking_state', '=', 'quotation'),
        ], order='create_date desc', limit=1)

        # If no quotation document exists, try to generate one
        if not invoice_document:
            _logger.info(f"No quotation PDF found for booking {self.name}, attempting to generate...")
            try:
                invoice_document = self.env['fleet.booking.invoice.document'].sudo().generate_invoice_pdf(
                    booking_id=self.id,
                    booking_state='quotation'
                )
            except Exception as e:
                _logger.error(f"Failed to generate quotation PDF for booking {self.name}: {str(e)}")
                return False

        if not invoice_document or not invoice_document.pdf_file:
            _logger.warning(f"No PDF file available in invoice document for booking {self.name}")
            return False

        # Get the ir.attachment ID for the PDF file
        attachment = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'fleet.booking.invoice.document'),
            ('res_id', '=', invoice_document.id),
            ('res_field', '=', 'pdf_file')
        ], limit=1)

        if not attachment:
            _logger.warning(f"No attachment found for invoice document {invoice_document.id}")
            return False

        # Build the public URL using the ATTACHMENT ID
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        pdf_url = "{}/web/content/{}".format(base_url, attachment.id)

        _logger.info(f"Generated quotation PDF URL for booking {self.name}: {pdf_url} (Attachment ID: {attachment.id})")
        return pdf_url

    def _generate_quotation_pdf_url(self):
        """Generate public URL for quotation PDF."""
        self.ensure_one()

        try:
            invoice_doc_url = self._get_quotation_pdf_url_from_invoice_document()
            if invoice_doc_url:
                return invoice_doc_url
        except Exception as e:
            _logger.warning(f"Could not get PDF URL from invoice document: {str(e)}")

        if hasattr(self, 'invoice_url') and self.invoice_url:
            return self.invoice_url

        base_url = self.get_base_url()
        if hasattr(self, 'invoice_access_token'):
            if not self.invoice_access_token:
                self._auto_generate_invoice_access_token()
            quotation_url = f"{base_url}/fleet/booking/{self.id}/quotation/{self.invoice_access_token}"
            return quotation_url

        return False

    def _generate_confirmation_receipt_pdf_url(self):
        """Generate public URL for confirmation receipt PDF (similar to quotation)."""
        self.ensure_one()

        try:
            receipt_doc_url = self._get_confirmation_pdf_url_from_invoice_document()
            if receipt_doc_url:
                return receipt_doc_url
        except Exception as e:
            _logger.warning(f"Could not get receipt PDF URL from invoice document: {str(e)}")

        if hasattr(self, 'invoice_url') and self.invoice_url:
            return self.invoice_url

        base_url = self.get_base_url()
        if hasattr(self, 'invoice_access_token'):
            if not self.invoice_access_token:
                self._auto_generate_invoice_access_token()
            receipt_url = f"{base_url}/fleet/booking/{self.id}/invoice/{self.invoice_access_token}"
            return receipt_url

        return False

    def _send_quotation_template(self):
        """Send quotation WhatsApp template with PDF"""
        self.ensure_one()

        if self.quotation_template_sent:
            _logger.info(f"Quotation template already sent for booking {self.name}")
            return False

        if not self.customer_phone:
            _logger.warning(f"Cannot send quotation template for booking {self.name}: Customer phone missing")
            self.message_post(
                body=_('⚠️ Cannot send WhatsApp quotation: Customer phone number is missing'),
                message_type='notification'
            )
            return False

        try:
            config = self.env['interakt.config'].get_active_config()

            template = self.env['interakt.template'].search([
                ('template_code', '=', 'quotation_temp'),
                ('active', '=', True)
            ], limit=1)

            if not template:
                _logger.warning("Quotation template 'quotation_temp' not found")
                self.message_post(
                    body=_('⚠️ Cannot send WhatsApp quotation: Template not configured'),
                    message_type='notification'
                )
                return False

            country_code = '+91'
            phone = self.customer_phone.replace('+', '').replace('-', '').replace(' ', '')
            if phone.startswith('91'):
                phone = phone[2:]

            config.create_or_update_user(
                phone=phone,
                country_code=country_code,
                user_name=self.customer_id.name or 'Customer',
                user_id=f"customer_{self.customer_id.id}"
            )

            quotation_pdf_url = self._generate_quotation_pdf_url()

            if not quotation_pdf_url:
                _logger.warning(f"Could not generate quotation PDF URL for booking {self.name}")
                self.message_post(
                    body=_('⚠️ Cannot send WhatsApp quotation: Failed to generate PDF URL'),
                    message_type='notification'
                )
                return False

            self.quotation_pdf_url = quotation_pdf_url

            body_values = [
                self.customer_id.name or "Valued Customer",
            ]

            _logger.info(f"Sending quotation template to {phone} for booking {self.name}")
            _logger.info(f"Quotation PDF URL: {quotation_pdf_url}")

            result = config.send_template_message(
                phone=phone,
                country_code=country_code,
                template_name='quotation_temp',
                body_values=body_values,
                header_url=quotation_pdf_url,
                callback_data=f"booking_quotation_{self.id}"
            )

            log_vals = {
                'config_id': config.id,
                'template_id': template.id,
                'phone_number': phone,
                'country_code': country_code,
                'recipient_name': self.customer_id.name,
                'template_name': 'quotation_temp',
                'body_values': json.dumps(body_values),
                'header_url': quotation_pdf_url,
                'callback_data': f"booking_quotation_{self.id}",
                'model_name': 'fleet.booking',
                'res_id': self.id,
            }

            if result.get('status') == 'success':
                log_vals.update({
                    'status': 'sent',
                    'message_id': result.get('message_id'),
                    'sent_date': fields.Datetime.now(),
                })

                self.write({
                    'quotation_template_sent': True,
                    'quotation_sent_date': fields.Datetime.now(),
                    'quotation_message_id': result.get('message_id'),
                })

                self.message_post(
                    body=_(
                        '✅ WhatsApp quotation sent successfully!<br/>'
                        'Template: <b>quotation_temp</b><br/>'
                        'Phone: <b>%s</b><br/>'
                        'PDF URL: <b>%s</b><br/>'
                        'Message ID: <b>%s</b>'
                    ) % (phone, quotation_pdf_url, result.get('message_id')),
                    message_type='notification'
                )

                _logger.info(f"Quotation template sent successfully for booking {self.name}")
            else:
                error_msg = result.get('message', 'Unknown error')
                log_vals.update({
                    'status': 'failed',
                    'error_message': error_msg,
                })

                self.message_post(
                    body=_(
                        '❌ Failed to send WhatsApp quotation<br/>'
                        'Error: <b>%s</b><br/>'
                        'Phone: <b>%s</b>'
                    ) % (error_msg, phone),
                    message_type='notification'
                )

                _logger.error(f"Failed to send quotation template for booking {self.name}: {error_msg}")

            self.env['interakt.message.log'].create(log_vals)

            return result.get('status') == 'success'

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Exception while sending quotation template for booking {self.name}: {error_msg}")

            self.env['interakt.message.log'].create({
                'template_name': 'quotation_temp',
                'phone_number': self.customer_phone,
                'recipient_name': self.customer_id.name,
                'status': 'failed',
                'error_message': error_msg,
                'model_name': 'fleet.booking',
                'res_id': self.id,
            })

            self.message_post(
                body=_(
                    '❌ Exception occurred while sending WhatsApp quotation<br/>'
                    'Error: <b>%s</b>'
                ) % error_msg,
                message_type='notification'
            )

            return False

    def _send_confirmation_template(self):
        """Send confirmation WhatsApp template with image header"""
        self.ensure_one()

        if self.confirmation_template_sent:
            _logger.info(f"Confirmation template already sent for booking {self.name}")
            return False

        if not self.customer_phone:
            _logger.warning(f"Cannot send confirmation template for booking {self.name}: Customer phone missing")
            self.message_post(
                body=_('⚠️ Cannot send WhatsApp confirmation: Customer phone number is missing'),
                message_type='notification'
            )
            return False

        try:
            config = self.env['interakt.config'].get_active_config()

            template = self.env['interakt.template'].search([
                ('template_code', '=', 'confirm'),
                ('active', '=', True)
            ], limit=1)

            if not template:
                _logger.warning("Confirmation template 'confirm' not found")
                self.message_post(
                    body=_('⚠️ Cannot send WhatsApp confirmation: Template not configured'),
                    message_type='notification'
                )
                return False

            country_code = '+91'
            phone = self.customer_phone.replace('+', '').replace('-', '').replace(' ', '')
            if phone.startswith('91'):
                phone = phone[2:]

            config.create_or_update_user(
                phone=phone,
                country_code=country_code,
                user_name=self.customer_id.name or 'Customer',
                user_id=f"customer_{self.customer_id.id}"
            )

            confirmation_header_url = "https://interaktprodmediastorage.blob.core.windows.net/mediaprodstoragecontainer/d609fe61-1955-4a98-9f1d-6a2b83f9b915/message_template_media/v7bo9SErsdKm/confirm.jpeg?se=2030-12-26T05%3A48%3A41Z&sp=rt&sv=2019-12-12&sr=b&sig=104sMcSLU4pH0K6/urSFfztFHFy0e53k7sRUvVLvTxA%3D"

            body_values = [
                self.customer_id.name or "Valued Customer",
                self.name or "N/A",
                self.journey_start_date.strftime('%B %d, %Y') if self.journey_start_date else "TBD",
                self.journey_start_time or "TBD",
                self.journey_start_location or "Not specified",
            ]

            _logger.info(f"Sending confirmation template to {phone} for booking {self.name}")

            result = config.send_template_message(
                phone=phone,
                country_code=country_code,
                template_name='confirm',
                body_values=body_values,
                header_url=confirmation_header_url,
                callback_data=f"booking_confirmation_{self.id}"
            )

            log_vals = {
                'config_id': config.id,
                'template_id': template.id,
                'phone_number': phone,
                'country_code': country_code,
                'recipient_name': self.customer_id.name,
                'template_name': 'confirm',
                'body_values': json.dumps(body_values),
                'header_url': confirmation_header_url,
                'callback_data': f"booking_confirmation_{self.id}",
                'model_name': 'fleet.booking',
                'res_id': self.id,
            }

            if result.get('status') == 'success':
                log_vals.update({
                    'status': 'sent',
                    'message_id': result.get('message_id'),
                    'sent_date': fields.Datetime.now(),
                })

                self.write({
                    'confirmation_template_sent': True,
                    'confirmation_sent_date': fields.Datetime.now(),
                    'confirmation_message_id': result.get('message_id'),
                })

                self.message_post(
                    body=_(
                        '✅ WhatsApp confirmation sent successfully!<br/>'
                        'Template: <b>confirm</b><br/>'
                        'Phone: <b>%s</b><br/>'
                        'Message ID: <b>%s</b>'
                    ) % (phone, result.get('message_id')),
                    message_type='notification'
                )

                _logger.info(f"Confirmation template sent successfully for booking {self.name}")

                # NEW: Schedule confirm_receipt template to send after 5 seconds
                self._schedule_confirmation_receipt_template()
            else:
                error_msg = result.get('message', 'Unknown error')
                log_vals.update({
                    'status': 'failed',
                    'error_message': error_msg,
                })

                self.message_post(
                    body=_(
                        '❌ Failed to send WhatsApp confirmation<br/>'
                        'Error: <b>%s</b><br/>'
                        'Phone: <b>%s</b>'
                    ) % (error_msg, phone),
                    message_type='notification'
                )

                _logger.error(f"Failed to send confirmation template for booking {self.name}: {error_msg}")

            self.env['interakt.message.log'].create(log_vals)

            return result.get('status') == 'success'

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Exception while sending confirmation template for booking {self.name}: {error_msg}")

            self.env['interakt.message.log'].create({
                'template_name': 'confirm',
                'phone_number': self.customer_phone,
                'recipient_name': self.customer_id.name,
                'status': 'failed',
                'error_message': error_msg,
                'model_name': 'fleet.booking',
                'res_id': self.id,
            })

            self.message_post(
                body=_(
                    '❌ Exception occurred while sending WhatsApp confirmation<br/>'
                    'Error: <b>%s</b>'
                ) % error_msg,
                message_type='notification'
            )

            return False

    def _schedule_confirmation_receipt_template(self):
        """Schedule confirm_receipt template to send after 5 seconds"""
        self.ensure_one()

        def delayed_send():
            """Function to be called after 5 seconds delay"""
            time.sleep(5)  # Wait for 5 seconds

            # Need to get fresh database cursor in thread
            with self.pool.cursor() as new_cr:
                try:
                    # Create new environment with new cursor
                    new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                    booking = new_env['fleet.booking'].browse(self.id)

                    # Send the receipt template
                    booking._send_confirmation_receipt_template()

                    # Commit the transaction
                    new_cr.commit()
                except Exception as e:
                    _logger.error(f"Error sending delayed confirmation receipt: {str(e)}")
                    new_cr.rollback()

        # Start thread to send after 5 seconds
        thread = threading.Thread(target=delayed_send)
        thread.daemon = True
        thread.start()

        _logger.info(f"Scheduled confirmation receipt template for booking {self.name} (will send in 5 seconds)")

    def _send_confirmation_receipt_template(self):
        """Send confirmation receipt WhatsApp template with PDF (sent 5 seconds after confirm)"""
        self.ensure_one()

        if self.confirmation_receipt_sent:
            _logger.info(f"Confirmation receipt template already sent for booking {self.name}")
            return False

        if not self.customer_phone:
            _logger.warning(f"Cannot send confirmation receipt for booking {self.name}: Customer phone missing")
            self.message_post(
                body=_('⚠️ Cannot send WhatsApp receipt: Customer phone number is missing'),
                message_type='notification'
            )
            return False

        try:
            config = self.env['interakt.config'].get_active_config()

            template = self.env['interakt.template'].search([
                ('template_code', '=', 'confirm_receipt'),
                ('active', '=', True)
            ], limit=1)

            if not template:
                _logger.warning("Confirmation receipt template 'confirm_receipt' not found")
                self.message_post(
                    body=_('⚠️ Cannot send WhatsApp receipt: Template not configured'),
                    message_type='notification'
                )
                return False

            country_code = '+91'
            phone = self.customer_phone.replace('+', '').replace('-', '').replace(' ', '')
            if phone.startswith('91'):
                phone = phone[2:]

            config.create_or_update_user(
                phone=phone,
                country_code=country_code,
                user_name=self.customer_id.name or 'Customer',
                user_id=f"customer_{self.customer_id.id}"
            )

            # Generate confirmation receipt PDF URL (similar to quotation)
            receipt_pdf_url = self._generate_confirmation_receipt_pdf_url()

            if not receipt_pdf_url:
                _logger.warning(f"Could not generate receipt PDF URL for booking {self.name}")
                self.message_post(
                    body=_('⚠️ Cannot send WhatsApp receipt: Failed to generate PDF URL'),
                    message_type='notification'
                )
                return False

            self.confirmation_receipt_pdf_url = receipt_pdf_url

            body_values = [
                self.customer_id.name or "Valued Customer",
            ]

            _logger.info(f"Sending confirmation receipt template to {phone} for booking {self.name}")
            _logger.info(f"Receipt PDF URL: {receipt_pdf_url}")

            result = config.send_template_message(
                phone=phone,
                country_code=country_code,
                template_name='confirm_receipt',
                body_values=body_values,
                header_url=receipt_pdf_url,  # PDF URL in header
                callback_data=f"booking_receipt_{self.id}"
            )

            log_vals = {
                'config_id': config.id,
                'template_id': template.id,
                'phone_number': phone,
                'country_code': country_code,
                'recipient_name': self.customer_id.name,
                'template_name': 'confirm_receipt',
                'body_values': json.dumps(body_values),
                'header_url': receipt_pdf_url,
                'callback_data': f"booking_receipt_{self.id}",
                'model_name': 'fleet.booking',
                'res_id': self.id,
            }

            if result.get('status') == 'success':
                log_vals.update({
                    'status': 'sent',
                    'message_id': result.get('message_id'),
                    'sent_date': fields.Datetime.now(),
                })

                self.write({
                    'confirmation_receipt_sent': True,
                    'confirmation_receipt_sent_date': fields.Datetime.now(),
                    'confirmation_receipt_message_id': result.get('message_id'),
                })

                self.message_post(
                    body=_(
                        '✅ WhatsApp confirmation receipt sent successfully!<br/>'
                        'Template: <b>confirm_receipt</b><br/>'
                        'Phone: <b>%s</b><br/>'
                        'PDF URL: <b>%s</b><br/>'
                        'Message ID: <b>%s</b>'
                    ) % (phone, receipt_pdf_url, result.get('message_id')),
                    message_type='notification'
                )

                _logger.info(f"Confirmation receipt template sent successfully for booking {self.name}")
            else:
                error_msg = result.get('message', 'Unknown error')
                log_vals.update({
                    'status': 'failed',
                    'error_message': error_msg,
                })

                self.message_post(
                    body=_(
                        '❌ Failed to send WhatsApp receipt<br/>'
                        'Error: <b>%s</b><br/>'
                        'Phone: <b>%s</b>'
                    ) % (error_msg, phone),
                    message_type='notification'
                )

                _logger.error(f"Failed to send confirmation receipt template for booking {self.name}: {error_msg}")

            self.env['interakt.message.log'].create(log_vals)

            return result.get('status') == 'success'

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Exception while sending confirmation receipt template for booking {self.name}: {error_msg}")

            self.env['interakt.message.log'].create({
                'template_name': 'confirm_receipt',
                'phone_number': self.customer_phone,
                'recipient_name': self.customer_id.name,
                'status': 'failed',
                'error_message': error_msg,
                'model_name': 'fleet.booking',
                'res_id': self.id,
            })

            self.message_post(
                body=_(
                    '❌ Exception occurred while sending WhatsApp receipt<br/>'
                    'Error: <b>%s</b>'
                ) % error_msg,
                message_type='notification'
            )

            return False

    def _send_followup_template(self):
        """Send followup WhatsApp template"""
        self.ensure_one()

        if self.followup_template_sent:
            _logger.info(f"Followup template already sent for booking {self.name}")
            return False

        if not self.customer_phone:
            _logger.warning(f"Cannot send followup template for booking {self.name}: Customer phone missing")
            self.message_post(
                body=_('⚠️ Cannot send WhatsApp followup: Customer phone number is missing'),
                message_type='notification'
            )
            return False

        try:
            config = self.env['interakt.config'].get_active_config()

            template = self.env['interakt.template'].search([
                ('template_code', '=', 'followup'),
                ('active', '=', True)
            ], limit=1)

            if not template:
                _logger.warning("Followup template 'followup' not found")
                self.message_post(
                    body=_('⚠️ Cannot send WhatsApp followup: Template not configured'),
                    message_type='notification'
                )
                return False

            country_code = '+91'
            phone = self.customer_phone.replace('+', '').replace('-', '').replace(' ', '')
            if phone.startswith('91'):
                phone = phone[2:]

            config.create_or_update_user(
                phone=phone,
                country_code=country_code,
                user_name=self.customer_id.name or 'Customer',
                user_id=f"customer_{self.customer_id.id}"
            )

            followup_header_url = "https://interaktprodmediastorage.blob.core.windows.net/mediaprodstoragecontainer/d609fe61-1955-4a98-9f1d-6a2b83f9b915/message_template_media/s2zPodsOLWpw/feedback.png?se=2030-12-26T13%3A08%3A50Z&sp=rt&sv=2019-12-12&sr=b&sig=dXT3X2p6pnnYI%2Bc8MxA6hKevw6fsN2pTOgYJDeaurGs%3D"

            body_values = [
                self.customer_id.name or "Valued Customer",
            ]

            _logger.info(f"Sending followup template to {phone} for booking {self.name}")

            result = config.send_template_message(
                phone=phone,
                country_code=country_code,
                template_name='followup',
                body_values=body_values,
                header_url=followup_header_url,
                callback_data=f"booking_followup_{self.id}"
            )

            log_vals = {
                'config_id': config.id,
                'template_id': template.id,
                'phone_number': phone,
                'country_code': country_code,
                'recipient_name': self.customer_id.name,
                'template_name': 'followup',
                'body_values': json.dumps(body_values),
                'header_url': followup_header_url,
                'callback_data': f"booking_followup_{self.id}",
                'model_name': 'fleet.booking',
                'res_id': self.id,
            }

            if result.get('status') == 'success':
                log_vals.update({
                    'status': 'sent',
                    'message_id': result.get('message_id'),
                    'sent_date': fields.Datetime.now(),
                })

                self.write({
                    'followup_template_sent': True,
                    'followup_sent_date': fields.Datetime.now(),
                    'followup_message_id': result.get('message_id'),
                })

                self.message_post(
                    body=_(
                        '✅ WhatsApp followup sent successfully!<br/>'
                        'Template: <b>followup</b><br/>'
                        'Phone: <b>%s</b><br/>'
                        'Message ID: <b>%s</b>'
                    ) % (phone, result.get('message_id')),
                    message_type='notification'
                )

                _logger.info(f"Followup template sent successfully for booking {self.name}")
            else:
                error_msg = result.get('message', 'Unknown error')
                log_vals.update({
                    'status': 'failed',
                    'error_message': error_msg,
                })

                self.message_post(
                    body=_(
                        '❌ Failed to send WhatsApp followup<br/>'
                        'Error: <b>%s</b><br/>'
                        'Phone: <b>%s</b>'
                    ) % (error_msg, phone),
                    message_type='notification'
                )

                _logger.error(f"Failed to send followup template for booking {self.name}: {error_msg}")

            self.env['interakt.message.log'].create(log_vals)

            return result.get('status') == 'success'

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Exception while sending followup template for booking {self.name}: {error_msg}")

            self.env['interakt.message.log'].create({
                'template_name': 'followup',
                'phone_number': self.customer_phone,
                'recipient_name': self.customer_id.name,
                'status': 'failed',
                'error_message': error_msg,
                'model_name': 'fleet.booking',
                'res_id': self.id,
            })

            self.message_post(
                body=_(
                    '❌ Exception occurred while sending WhatsApp followup<br/>'
                    'Error: <b>%s</b>'
                ) % error_msg,
                message_type='notification'
            )

            return False

    # Action methods for manual resending
    def action_resend_quotation_template(self):
        """Manual action to resend quotation template"""
        self.ensure_one()

        self.write({
            'quotation_template_sent': False,
            'quotation_sent_date': False,
            'quotation_message_id': False,
        })

        if self._send_quotation_template():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Quotation template sent successfully!'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Failed'),
                    'message': _('Failed to send quotation template. Check message logs for details.'),
                    'type': 'danger',
                }
            }

    def action_resend_confirmation_template(self):
        """Manual action to resend confirmation template"""
        self.ensure_one()

        self.write({
            'confirmation_template_sent': False,
            'confirmation_sent_date': False,
            'confirmation_message_id': False,
        })

        if self._send_confirmation_template():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Confirmation template sent successfully!'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Failed'),
                    'message': _('Failed to send confirmation template. Check message logs for details.'),
                    'type': 'danger',
                }
            }

    def action_resend_confirmation_receipt_template(self):
        """Manual action to resend confirmation receipt template"""
        self.ensure_one()

        self.write({
            'confirmation_receipt_sent': False,
            'confirmation_receipt_sent_date': False,
            'confirmation_receipt_message_id': False,
        })

        if self._send_confirmation_receipt_template():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Confirmation receipt sent successfully!'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Failed'),
                    'message': _('Failed to send confirmation receipt. Check message logs for details.'),
                    'type': 'danger',
                }
            }

    def action_send_followup_template(self):
        """Manual action to send followup template"""
        self.ensure_one()

        self.write({
            'followup_template_sent': False,
            'followup_sent_date': False,
            'followup_message_id': False,
        })

        if self._send_followup_template():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Followup template sent successfully!'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Failed'),
                    'message': _('Failed to send followup template. Check message logs for details.'),
                    'type': 'danger',
                }
            }

    def action_view_whatsapp_messages(self):
        """View WhatsApp messages for this booking"""
        self.ensure_one()
        return {
            'name': _('WhatsApp Messages'),
            'type': 'ir.actions.act_window',
            'res_model': 'interakt.message.log',
            'view_mode': 'tree,form',
            'domain': [('model_name', '=', 'fleet.booking'), ('res_id', '=', self.id)],
            'context': {
                'default_model_name': 'fleet.booking',
                'default_res_id': self.id,
            },
        }