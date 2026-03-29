# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class FleetBookingInherit(models.Model):
    _inherit = 'fleet.booking'

    # NEW: Relationship to invoice documents
    invoice_document_ids = fields.One2many(
        'fleet.booking.invoice.document',
        'booking_id',
        string='Invoice Documents',
        help='All generated invoice PDFs for this booking'
    )

    invoice_document_count = fields.Integer(
        string='Invoice Documents',
        compute='_compute_invoice_document_count',
        store=False
    )

    # NEW: Track if auto-generation is enabled for this booking
    auto_generate_invoices = fields.Boolean(
        string='Auto-Generate Invoices',
        default=True,
        help='Automatically generate invoice PDFs when stage changes'
    )

    @api.depends('invoice_document_ids')
    def _compute_invoice_document_count(self):
        """Compute count of invoice documents"""
        for record in self:
            record.invoice_document_count = len(record.invoice_document_ids)

    def write(self, vals):
        """Override write to automatically generate invoices on state change"""
        # Get old states before write
        old_states = {record.id: record.state for record in self}

        # Call super to update records
        result = super(FleetBookingInherit, self).write(vals)

        # Check if state changed and auto-generation is enabled
        if 'state' in vals:
            new_state = vals['state']

            # Define stages that trigger invoice generation
            trigger_stages = ['quotation', 'confirmed', 'completed']

            for record in self:
                old_state = old_states.get(record.id)

                # Only generate if:
                # 1. State actually changed
                # 2. Auto-generation is enabled
                # 3. New state is in trigger stages
                if (old_state != new_state and
                        record.auto_generate_invoices and
                        new_state in trigger_stages):

                    try:
                        # Generate invoice PDF asynchronously to avoid blocking
                        self.env['fleet.booking.invoice.document'].sudo().generate_invoice_pdf(
                            booking_id=record.id,
                            booking_state=new_state
                        )
                        _logger.info(
                            "Auto-generated invoice PDF for booking {} at stage {}".format(
                                record.name, new_state
                            )
                        )
                    except Exception as e:
                        # Log error but don't block the state change
                        _logger.error(
                            "Failed to auto-generate invoice PDF for booking {}: {}".format(
                                record.name, str(e)
                            )
                        )

                        # Optionally post error message in chatter
                        record.message_post(
                            body=_(
                                "Failed to auto-generate invoice PDF at stage %s: %s"
                            ) % (new_state, str(e)),
                            message_type='notification'
                        )

        return result

    def action_view_invoice_documents(self):
        """Action to view all invoice documents for this booking"""
        self.ensure_one()

        return {
            'name': _('Invoice Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.booking.invoice.document',
            'view_mode': 'tree,form',
            'domain': [('booking_id', '=', self.id)],
            'context': {
                'default_booking_id': self.id,
                'default_booking_state': self.state,
            },
            'target': 'current',
        }

    def action_generate_invoice_current_stage(self):
        """Manually generate invoice PDF for current stage"""
        self.ensure_one()

        try:
            # Generate PDF
            document = self.env['fleet.booking.invoice.document'].sudo().generate_invoice_pdf(
                booking_id=self.id,
                booking_state=self.state
            )

            if not document:
                raise UserError(_("Failed to generate invoice document."))

            # Open the generated document
            return {
                'type': 'ir.actions.act_window',
                'name': _('Generated Invoice'),
                'res_model': 'fleet.booking.invoice.document',
                'res_id': document.id,
                'view_mode': 'form',
                'target': 'new',
            }
        except Exception as e:
            _logger.error("Error generating invoice for current stage: {}".format(str(e)))
            raise UserError(_('Failed to generate invoice: %s') % str(e))

    def action_generate_all_stage_invoices(self):
        """Generate invoice PDFs for all applicable stages (only current and previous stages)"""
        self.ensure_one()

        try:
            # Validate that report exists
            report = self.env.ref('fleet_booking.action_report_fleet_booking_invoice', raise_if_not_found=False)
            if not report:
                raise UserError(_(
                    "Invoice report not found!\n"
                    "Please ensure the 'fleet_booking' module is properly installed "
                    "and the report 'action_report_fleet_booking_invoice' exists."
                ))

            # Define all stages in order
            all_stages = ['enquiry', 'quotation', 'followup', 'confirmed', 'completed', 'cancelled', 'feedback']

            # Get current stage index
            try:
                current_index = all_stages.index(self.state)
            except ValueError:
                raise UserError(_(
                    "Invalid booking state: %s\n"
                    "Cannot determine which invoices to generate."
                ) % self.state)

            # Only generate for stages up to current stage (excluding enquiry and followup)
            stages_to_generate = ['quotation', 'confirmed', 'completed']

            # Filter to only include stages we've reached or passed
            applicable_stages = []
            for stage in stages_to_generate:
                try:
                    stage_index = all_stages.index(stage)
                    if stage_index <= current_index:
                        applicable_stages.append(stage)
                except ValueError:
                    continue

            if not applicable_stages:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Information'),
                        'message': _(
                            'No applicable stages for PDF generation.\n'
                            'Current stage: %s\n'
                            'PDFs are generated for: Quotation, Confirmed, Completed stages.'
                        ) % dict(self._fields['state'].selection).get(self.state),
                        'type': 'info',
                        'sticky': True,
                    }
                }

            generated_count = 0
            failed_stages = []

            for stage in applicable_stages:
                try:
                    self.env['fleet.booking.invoice.document'].sudo().generate_invoice_pdf(
                        booking_id=self.id,
                        booking_state=stage
                    )
                    generated_count += 1
                    _logger.info("Successfully generated PDF for stage: {}".format(stage))
                except Exception as e:
                    failed_stages.append("{}: {}".format(stage, str(e)))
                    _logger.error("Failed to generate invoice for stage {}: {}".format(stage, str(e)))

            # Prepare result message
            if generated_count > 0:
                message = _('Successfully generated %s invoice PDF(s)') % generated_count
                if failed_stages:
                    message += _('\n\nFailed stages:\n%s') % '\n'.join(failed_stages)

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': message,
                        'type': 'success' if not failed_stages else 'warning',
                        'sticky': True,
                    }
                }
            else:
                error_details = '\n'.join(failed_stages) if failed_stages else 'Unknown error'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('Failed to generate any invoice PDFs.\n\nDetails:\n%s') % error_details,
                        'type': 'danger',
                        'sticky': True,
                    }
                }

        except UserError as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        except Exception as e:
            _logger.error("Unexpected error in action_generate_all_stage_invoices: {}".format(str(e)))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('An unexpected error occurred: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }