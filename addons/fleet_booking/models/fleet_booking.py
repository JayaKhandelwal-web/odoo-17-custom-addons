from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, time
import logging
import uuid
import secrets

_logger = logging.getLogger(__name__)


class FleetBooking(models.Model):
    _name = 'fleet.booking'
    _description = 'Fleet Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Order Reference', required=True, copy=False,
                       readonly=True, default=lambda self: _('New'))

    # UPDATED: Fields for shareable invoice URLs with automatic generation
    invoice_access_token = fields.Char(string='Invoice Access Token', copy=False, readonly=True)
    invoice_url = fields.Char(string='Shareable Invoice URL', compute='_compute_invoice_url', store=True)

    # NEW: Booking Type Selection
    booking_type = fields.Selection([
        ('individual', 'Individual'),
        ('company', 'Company'),
    ], string='Booking Type', default='individual', required=True, tracking=True)

    # Basic Info
    customer_id = fields.Many2one('res.partner', string='Customer',
                                  required=True, tracking=True)
    customer_email = fields.Char(related='customer_id.email', string='Email', readonly=False, store=True)
    customer_phone = fields.Char(related='customer_id.phone', string='Phone', readonly=False, store=True,  required=True)
    company_name = fields.Char(string='Company Name')
    route_id = fields.Many2one('fleet.route', string='Route')

    # Passenger Info
    passenger_name = fields.Char(string='Passenger Name')
    passenger_position = fields.Char(string='Passenger Position')
    passenger_email = fields.Char(string='Passenger Email')
    passenger_phone = fields.Char(string='Passenger Phone')
    passenger_count = fields.Integer(string='Passenger Count', default=0)

    # UPDATED: Status management with separate cancelled state
    state = fields.Selection([
        ('enquiry', 'Enquiry'),
        ('quotation', 'Quotation'),
        ('followup', 'Follow Up'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('feedback', 'Feedback'),
    ], string='Status', default='enquiry', tracking=True)

    # NEW: Cancellation fields
    is_cancelled = fields.Boolean(string='Is Cancelled', default=False, readonly=True)
    cancelled_date = fields.Datetime(string='Cancelled Date', readonly=True)
    cancelled_by = fields.Many2one('res.users', string='Cancelled By', readonly=True)
    cancellation_reason = fields.Text(string='Cancellation Reason', readonly=True)

    # NEW: Refund Management
    refund_policy = fields.Selection([
        ('full_refund', 'Full Refund'),
        ('partial_refund', 'Partial Refund'),
        ('no_refund', 'No Refund'),
    ], string='Refund Policy', tracking=True)

    refund_amount = fields.Monetary(string='Refund Amount', currency_field='currency_id',
                                    help='Amount to be refunded to customer')
    refund_percentage = fields.Float(string='Refund Percentage', digits=(5, 2),
                                     help='Percentage of total amount to be refunded')
    refund_processed = fields.Boolean(string='Refund Processed', default=False)
    refund_processed_date = fields.Datetime(string='Refund Processed Date')
    refund_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('adjustment', 'Adjustment'),
        ('other', 'Other'),
    ], string='Refund Method')
    refund_notes = fields.Text(string='Refund Notes')

    # NEW: Stage History for Go Back functionality
    previous_state = fields.Char(string='Previous State', readonly=True)
    stage_change_reason = fields.Text(string='Stage Change Reason')

    # Transport Details
    journey_start_location = fields.Char(string='Start Location', tracking=True, required=True)
    journey_end_location = fields.Char(string='End Location', tracking=True, required=True)
    via_stops = fields.Text(string='Via Stops')
    journey_distance = fields.Float(string='Distance', digits=(16, 2))
    distance_uom = fields.Selection([
        ('km', 'Kilometer'),
        ('mile', 'Mile')
    ], string='Distance UOM', default='km')

    journey_duration = fields.Integer(string='Duration (minutes)')
    journey_start_date = fields.Date(string='Travel Date', tracking=True, required=True)
    journey_start_time = fields.Selection(
        selection='_get_time_options',
        string='Start Time',
        default='08:00 AM'
    )
    fixed_end_time = fields.Boolean(string='Fixed End Time')
    return_journey_needed = fields.Boolean(string='Return Journey Needed')

    return_journey_date = fields.Date(string='Return Date', tracking=True)
    return_journey_time = fields.Selection(
        selection='_get_time_options',
        string='Return Time',
        default='08:00 AM'
    )

    # Vehicle Details - UPDATED for Simply Fleet integration
    vehicle_id = fields.Many2one('simply.fleet.vehicle', string='Vehicle',
                                 domain=[('state', '=', 'active')], tracking=True)
    vehicle_group_id = fields.Many2one('simply.fleet.vehicle.type', string='Vehicle Group', tracking=True)

    # Vehicle Type field with predefined options
    vehicle_type = fields.Selection([
        ('17_Seater_Luxury_force_Traveller', '17 Seater Luxury force Traveller'),
        ('26_Seater_Luxury_Force_Traveller', '26 Seater Luxury Force Traveller'),
        ('33_Seater_Super_Luxury_Recliner_AC_Coach', '33 Seater Super Luxury Recliner AC Coach'),
        ('41_Seater_Super_Luxury_Recliner_AC_Coach', '41 Seater Super Luxury Recliner AC Coach'),
        ('48_Seater_Luxury_AC_Coach', '48 Seater Luxury AC Coach'),
        ('49_Seater_Super_Luxury_AC_Coach_2024', '49 Seater Super Luxury AC Coach 2024'),
        ('50_Seater_Super_Luxury_AC_Coach_2025', '50 Seater Super Luxury AC Coach 2025'),
        ('Toyota_Innova', 'Toyota Innova'),
        ('Toyota_Innova_Crysta', 'Toyota Innova Crysta'),
        ('Ertiga', 'Ertiga'),
        ('Honda_Amaze', 'Honda Amaze'),
        ('Hyundai_Aura', 'Hyundai Aura'),
        ('Hyundai_Xcent', 'Hyundai Xcent'),
        ('Tavera', 'Tavera'),
    ], string='Vehicle Type', tracking=True)

    # Driver Assignment - Use HR Employee
    driver_id = fields.Many2one('hr.employee', string='Assigned Driver',
                                domain=[('job_title', 'ilike', 'driver')], tracking=True)

    # COMPUTED FIELDS FOR VEHICLE INFORMATION FROM SIMPLY FLEET
    vehicle_name = fields.Char(related='vehicle_id.name', string='Vehicle Name', readonly=True, store=True)
    vehicle_ref = fields.Char(related='vehicle_id.ref', string='Vehicle Reference', readonly=True, store=True)
    vehicle_brand = fields.Char(related='vehicle_id.brand', string='Vehicle Brand', readonly=True, store=True)
    vehicle_model = fields.Char(related='vehicle_id.model', string='Vehicle Model', readonly=True, store=True)
    vehicle_group_name = fields.Char(related='vehicle_group_id.name', string='Vehicle Group Name', readonly=True,
                                     store=True)

    # Financial Details
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    journey_price = fields.Monetary(string='Journey Price', currency_field='currency_id')
    # GST Calculation Type - NEW FIELD
    gst_type = fields.Selection([
        ('included', 'GST Included in Journey Price'),
        ('excluded', 'GST Excluded (Add to Journey Price)'),
    ], string='GST Type', default='excluded', required=True, tracking=True)

    # UPDATED: GST Percentage with 18% option
    gst_percentage = fields.Selection([
        ('0', '0%'),
        ('5', '5%'),
        ('18', '18%'),  # NEW: Added 18% option
    ], string='GST %', default='5', tracking=True)

    # NEW: Base Price (when GST is included, this is the price without GST)
    base_price = fields.Monetary(
        string='Base Price',
        currency_field='currency_id',
        compute='_compute_base_price',
        store=True,
        readonly=True,
        help='Price before GST (calculated when GST is included)'
    )

    vat_amount = fields.Monetary(string='GST', currency_field='currency_id',
                                 compute='_compute_gst_amount', store=True, readonly=True)
    total_price = fields.Monetary(string='Total', compute='_compute_total_price',
                                  store=True, currency_field='currency_id')

    # Payment Tracking
    payment_status = fields.Selection([
        ('not_invoiced', 'Not Invoiced'),
        ('invoiced', 'Invoiced'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ], string='Payment Status', default='not_invoiced', tracking=True)
    payment_date = fields.Datetime(string='Payment Date')
    payment_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('other', 'Other'),
    ], string='Payment Method')
    amount_paid = fields.Monetary(string='Amount Paid', currency_field='currency_id')
    balance_amount = fields.Monetary(string='Balance', compute='_compute_balance',
                                     store=True, currency_field='currency_id')

    # Notes
    notes = fields.Text(string='Order Notes')
    transport_notes = fields.Text(string='Transport Notes')

    # Activity tracking
    create_date = fields.Datetime(string='Created On', readonly=True)
    user_id = fields.Many2one('res.users', string='Assigned To',
                              default=lambda self: self.env.user)

    # Feedback
    feedback = fields.Text(string='Customer Feedback')
    feedback_rating = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars'),
    ], string='Rating')

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    route_map_url = fields.Char(string='Route Map URL')
    journey_duration_formatted = fields.Char(
        string='Duration (Formatted)',
        compute='_compute_duration_formatted'
    )

    # Terms and Conditions
    terms_template_id = fields.Many2one('fleet.booking.terms.template', string='Terms Template')
    terms_conditions = fields.Html(string='Terms & Conditions', help='Custom terms and conditions for this booking')
    # Add these NEW fields to your FleetBooking model:
    # NEW: WhatsApp Template Sending Fields
    whatsapp_template_sent = fields.Boolean(string='WhatsApp Template Sent', default=False, readonly=True)
    whatsapp_template_sent_date = fields.Datetime(string='Template Sent Date', readonly=True)
    whatsapp_template_name = fields.Char(string='Template Name Sent', readonly=True)
    whatsapp_message_id = fields.Char(string='WhatsApp Message ID', readonly=True)
    whatsapp_send_error = fields.Text(string='WhatsApp Send Error', readonly=True)

    # Add these NEW methods to your FleetBooking model:

    def _send_whatsapp_enquiry_template(self):
        """Send annapurna_enquiries template automatically when booking is created"""
        self.ensure_one()

        if not self.customer_phone:
            _logger.warning(f"Cannot send WhatsApp template for booking {self.name}: Customer phone number is missing")
            self.whatsapp_send_error = "Customer phone number is missing"
            return False

        try:
            config = self.env['myoperator.chat.config'].get_active_config()
            if not config:
                _logger.warning(
                    f"Cannot send WhatsApp template for booking {self.name}: No active MyOperator configuration found")
                self.whatsapp_send_error = "No active MyOperator configuration found"
                return False

            template_name = 'annapurna_enquiries'

            template_parameters = {
                "1": self.customer_id.name or "Valued Customer",
                "2": self.name or "New Booking",
            }

            _logger.info(
                f"Sending WhatsApp template '{template_name}' to {self.customer_phone} for booking {self.name}")

            # FIXED: Use correct method signature based on your MyOperator code
            result = config.send_message(
                phone_number=self.customer_phone,
                message_text='',  # Changed from 'message' to 'message_text'
                use_template=True,
                template_name=template_name,
                template_parameters=template_parameters
            )

            if result.get('status') == 'success':
                self.write({
                    'whatsapp_template_sent': True,
                    'whatsapp_template_sent_date': fields.Datetime.now(),
                    'whatsapp_template_name': template_name,
                    'whatsapp_message_id': result.get('message_id', 'Unknown'),
                    'whatsapp_send_error': False,
                })

                self.message_post(
                    body=_(
                        "WhatsApp enquiry template sent successfully!<br/>"
                        "Template: <b>%s</b><br/>"
                        "Phone: <b>%s</b><br/>"
                        "Message ID: <b>%s</b>"
                    ) % (template_name, self.customer_phone, result.get('message_id', 'Unknown')),
                    message_type='notification'
                )
                return True
            else:
                error_msg = result.get('message', 'Unknown error occurred')
                self.write({'whatsapp_send_error': error_msg})

                self.message_post(
                    body=_(
                        "Failed to send WhatsApp enquiry template.<br/>"
                        "Error: <b>%s</b><br/>"
                        "Template: <b>%s</b><br/>"
                        "Phone: <b>%s</b>"
                    ) % (error_msg, template_name, self.customer_phone),
                    message_type='notification'
                )
                return False

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Exception while sending WhatsApp template for booking {self.name}: {error_msg}")

            self.write({'whatsapp_send_error': error_msg})

            self.message_post(
                body=_(
                    "Exception occurred while sending WhatsApp enquiry template.<br/>"
                    "Error: <b>%s</b><br/>"
                    "Phone: <b>%s</b>"
                ) % (error_msg, self.customer_phone or 'Not provided'),
                message_type='notification'
            )
            return False

    def action_resend_whatsapp_template(self):
        """Manual action to resend WhatsApp enquiry template"""
        self.ensure_one()

        if self._send_whatsapp_enquiry_template():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('WhatsApp Template Sent'),
                    'message': _('Enquiry template sent successfully to %s') % self.customer_phone,
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('WhatsApp Template Failed'),
                    'message': _('Failed to send template. Error: %s') % (self.whatsapp_send_error or 'Unknown error'),
                    'type': 'danger',
                }
            }
    # UPDATED: Compute invoice URL with dependency on invoice_access_token
    @api.depends('invoice_access_token')
    def _compute_invoice_url(self):
        for booking in self:
            if booking.invoice_access_token:
                base_url = booking.get_base_url()
                booking.invoice_url = f"{base_url}/fleet/booking/{booking.id}/invoice/{booking.invoice_access_token}"
            else:
                booking.invoice_url = False

    # UPDATED: Auto-generate access token for invoice sharing
    def _auto_generate_invoice_access_token(self):
        """Automatically generate a unique access token for invoice sharing"""
        self.ensure_one()
        if not self.invoice_access_token:
            # Generate a secure random token
            self.invoice_access_token = secrets.token_urlsafe(32)
            _logger.info(f"Auto-generated invoice access token for booking {self.name}")
        return self.invoice_access_token

    # NEW: Method to get valid previous states for go back functionality
    def _get_previous_state_mapping(self):
        """Define valid previous states for each current state"""
        return {
            'quotation': 'enquiry',
            'followup': 'quotation',
            'confirmed': 'followup',
            'completed': 'confirmed',
            'feedback': 'completed',
            # Cancelled can go back to any previous state before cancellation
        }

    def _can_go_back(self):
        """Check if current state allows going back to previous state"""
        if self.state == 'cancelled':
            return False  # Cannot go back from cancelled state
        previous_states = self._get_previous_state_mapping()
        return self.state in previous_states

    def _get_go_back_state(self):
        """Get the previous state for current state"""
        previous_states = self._get_previous_state_mapping()
        return previous_states.get(self.state)

    # NEW: Validation for Company Name based on Booking Type
    @api.constrains('booking_type', 'company_name')
    def _check_company_name_required(self):
        for record in self:
            if record.booking_type == 'company' and not record.company_name:
                raise ValidationError(_("Company Name is required when Booking Type is 'Company'."))

    # NEW: OnChange method to clear company name when booking type changes to individual
    @api.onchange('booking_type')
    def _onchange_booking_type(self):
        if self.booking_type == 'individual':
            self.company_name = False

    # NEW: OnChange for refund percentage
    @api.onchange('refund_percentage', 'total_price')
    def _onchange_refund_percentage(self):
        if self.refund_percentage and self.total_price:
            self.refund_amount = (self.refund_percentage / 100.0) * self.total_price

    @api.onchange('refund_amount', 'total_price')
    def _onchange_refund_amount(self):
        if self.refund_amount and self.total_price:
            self.refund_percentage = (self.refund_amount / self.total_price) * 100.0

    # ONCHANGE METHODS FOR SIMPLY FLEET INTEGRATION
    @api.onchange('vehicle_group_id')
    def _onchange_vehicle_group(self):
        """Filter vehicles based on selected vehicle group"""
        if self.vehicle_group_id:
            # Clear current vehicle selection if it doesn't match the group
            if self.vehicle_id and self.vehicle_id.vehicle_type_id != self.vehicle_group_id:
                self.vehicle_id = False
            return {
                'domain': {
                    'vehicle_id': [
                        ('vehicle_type_id', '=', self.vehicle_group_id.id),
                        ('state', '=', 'active')
                    ]
                }
            }
        else:
            return {
                'domain': {
                    'vehicle_id': [('state', '=', 'active')]
                }
            }

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        """Update vehicle group and driver when vehicle is selected"""
        if self.vehicle_id:
            try:
                self.vehicle_group_id = self.vehicle_id.vehicle_type_id
                # FIXED: Check if vehicle has driver_id field before accessing it
                if hasattr(self.vehicle_id, 'driver_id') and self.vehicle_id.driver_id:
                    self.driver_id = self.vehicle_id.driver_id
            except Exception as e:
                _logger.warning(f"Error in vehicle onchange: {e}")

    @api.onchange('terms_template_id')
    def _onchange_terms_template(self):
        """Apply the selected template to terms_conditions"""
        if self.terms_template_id:
            self.terms_conditions = self.terms_template_id.template_content

    # COMPUTED METHODS
    @api.depends('journey_price', 'vat_amount', 'gst_type')
    def _compute_total_price(self):
        """
        Calculate total price based on GST type
        - Excluded: total = journey_price + gst_amount
        - Included: total = journey_price (GST already included)
        """
        for record in self:
            if record.gst_type == 'excluded':
                # Add GST to journey price
                record.total_price = record.journey_price + record.vat_amount
            else:  # included
                # Journey price already includes GST
                record.total_price = record.journey_price

    @api.depends('journey_price', 'gst_percentage', 'gst_type')
    def _compute_gst_amount(self):
        """
        Calculate GST based on whether it's included or excluded
        - Excluded: GST = journey_price * gst_rate
        - Included: GST = journey_price - (journey_price / (1 + gst_rate))
        """
        for record in self:
            if record.journey_price and record.gst_percentage:
                gst_rate = float(record.gst_percentage) / 100.0

                if record.gst_type == 'excluded':
                    # GST is added on top of journey price
                    record.vat_amount = record.journey_price * gst_rate
                else:  # included
                    # GST is already in the journey price, extract it
                    record.vat_amount = record.journey_price - (record.journey_price / (1 + gst_rate))
            else:
                record.vat_amount = 0.0

    @api.depends('journey_price', 'gst_percentage', 'gst_type')
    def _compute_base_price(self):
        """
        Calculate base price (price before GST)
        - Excluded: base_price = journey_price
        - Included: base_price = journey_price / (1 + gst_rate)
        """
        for record in self:
            if record.journey_price and record.gst_percentage:
                gst_rate = float(record.gst_percentage) / 100.0

                if record.gst_type == 'excluded':
                    # Base price is same as journey price
                    record.base_price = record.journey_price
                else:  # included
                    # Extract base price from journey price
                    record.base_price = record.journey_price / (1 + gst_rate)
            else:
                record.base_price = record.journey_price

    @api.depends('total_price', 'amount_paid', 'refund_amount')
    def _compute_balance(self):
        for record in self:
            if record.state == 'cancelled' and record.refund_amount:
                record.balance_amount = record.amount_paid - record.refund_amount
            else:
                record.balance_amount = record.total_price - record.amount_paid

    @api.depends('journey_duration')
    def _compute_duration_formatted(self):
        for record in self:
            if record.journey_duration:
                hours = int(record.journey_duration // 60)
                minutes = int(record.journey_duration % 60)
                record.journey_duration_formatted = f"{hours}h {minutes}m"
            else:
                record.journey_duration_formatted = "0h 0m"

    # CRUD METHODS
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.booking') or _('New')
            vals['previous_state'] = vals.get('state', 'enquiry')

        records = super(FleetBooking, self).create(vals_list)

        for record in records:
            if not record.invoice_access_token:
                record._auto_generate_invoice_access_token()
                record.message_post(
                    body=_("Invoice URL automatically generated for new booking %s at enquiry stage. URL: %s") % (
                        record.name, record.invoice_url
                    ),
                    message_type='notification'
                )

            # NEW: Send WhatsApp enquiry template automatically
            self.env.cr.commit()

            try:
                _logger.info(f"Attempting to send WhatsApp enquiry template for new booking {record.name}")
                record._send_whatsapp_enquiry_template()
            except Exception as e:
                _logger.error(f"Failed to send WhatsApp template for new booking {record.name}: {str(e)}")
                record.whatsapp_send_error = f"Failed to send template: {str(e)}"

        return records

    # UPDATED: Write method with automatic invoice URL generation at enquiry stage
    def write(self, vals):
        # Track state changes for go back functionality
        if 'state' in vals:
            for record in self:
                vals['previous_state'] = record.state

        # Call parent write first
        result = super(FleetBooking, self).write(vals)

        # UPDATED: Auto-generate invoice URL when state changes to enquiry (or any stage if not already generated)
        if 'state' in vals:
            for record in self:
                if not record.invoice_access_token:
                    record._auto_generate_invoice_access_token()
                    # Don't change payment status to invoiced at enquiry stage
                    if vals['state'] in ['confirmed', 'completed']:
                        record.payment_status = 'invoiced'

                    # Log message in chatter
                    record.message_post(
                        body=_("Invoice URL automatically generated for booking %s at %s stage. URL: %s") % (
                            record.name, dict(record._fields['state'].selection).get(vals['state'], vals['state']),
                            record.invoice_url
                        ),
                        message_type='notification'
                    )
                    _logger.info(f"Auto-generated invoice URL for booking {record.name} in state {vals['state']}")

        return result

    # NEW: Cancel Booking Action
    def action_cancel_booking(self):
        """Open wizard to cancel booking with mandatory reason and refund details"""
        self.ensure_one()

        if self.state == 'cancelled':
            raise UserError(_("This booking is already cancelled."))

        if self.state == 'completed':
            raise UserError(_("Cannot cancel a completed booking."))

        return {
            'name': _('Cancel Booking'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.booking.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_booking_id': self.id,
                'default_total_amount': self.total_price,
                'default_paid_amount': self.amount_paid,
            },
        }

    def cancel_booking_with_details(self, reason, refund_policy, refund_amount=0.0, refund_percentage=0.0,
                                    refund_notes=''):
        """Cancel booking with reason and refund details"""
        self.ensure_one()

        if self.state == 'cancelled':
            raise UserError(_("This booking is already cancelled."))

        if not reason:
            raise UserError(_("Cancellation reason is mandatory."))

        # Calculate refund amount if percentage is provided
        if refund_percentage and not refund_amount:
            refund_amount = (refund_percentage / 100.0) * self.total_price

        # Update booking status
        self.write({
            'state': 'cancelled',
            'is_cancelled': True,
            'cancelled_date': fields.Datetime.now(),
            'cancelled_by': self.env.user.id,
            'cancellation_reason': reason,
            'refund_policy': refund_policy,
            'refund_amount': refund_amount,
            'refund_percentage': refund_percentage if refund_percentage else (
                refund_amount / self.total_price * 100.0 if self.total_price else 0),
            'refund_notes': refund_notes,
        })

        # Update payment status based on refund policy
        if refund_policy == 'full_refund':
            self.payment_status = 'refunded'
        elif refund_policy == 'partial_refund':
            self.payment_status = 'partially_refunded'

        # Release vehicle
        if self.vehicle_id:
            try:
                self.vehicle_id.write({'state': 'active'})
            except:
                _logger.warning("Could not reset vehicle state to active")

        # Post message in chatter
        self.message_post(
            body=_("Booking <b>CANCELLED</b><br/>Reason: %s<br/>Refund Policy: %s<br/>Refund Amount: %s") % (
                reason, dict(self._fields['refund_policy'].selection)[refund_policy], refund_amount
            ),
            message_type='notification'
        )

    # NEW: Process Refund Action
    def action_process_refund(self):
        """Mark refund as processed"""
        self.ensure_one()

        if not self.is_cancelled:
            raise UserError(_("This booking is not cancelled."))

        if self.refund_processed:
            raise UserError(_("Refund has already been processed."))

        if self.refund_policy == 'no_refund':
            raise UserError(_("No refund is applicable for this booking."))

        return {
            'name': _('Process Refund'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.booking.refund.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_booking_id': self.id,
                'default_refund_amount': self.refund_amount,
            },
        }

    def process_refund_with_details(self, refund_method, refund_notes=''):
        """Process refund with method and notes"""
        self.ensure_one()

        self.write({
            'refund_processed': True,
            'refund_processed_date': fields.Datetime.now(),
            'refund_method': refund_method,
            'refund_notes': refund_notes,
        })

        # Post message in chatter
        self.message_post(
            body=_("Refund <b>PROCESSED</b><br/>Amount: %s<br/>Method: %s<br/>Notes: %s") % (
                self.refund_amount, dict(self._fields['refund_method'].selection)[refund_method], refund_notes
            ),
            message_type='notification'
        )

    # NEW: Go Back One Stage Action
    def action_go_back_one_stage(self):
        """Open wizard to go back to previous stage with mandatory reason"""
        self.ensure_one()

        if not self._can_go_back():
            raise UserError(
                _("Cannot go back from current stage '%s'.") % dict(self._fields['state'].selection)[self.state])

        return {
            'name': _('Go Back One Stage'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.booking.go.back.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_booking_id': self.id,
                'default_current_state': self.state,
                'default_previous_state': self._get_go_back_state(),
            },
        }

    def go_back_with_reason(self, reason):
        """Go back to previous stage with reason"""
        self.ensure_one()

        if not self._can_go_back():
            raise UserError(_("Cannot go back from current stage."))

        if not reason:
            raise UserError(_("Reason is mandatory when going back to previous stage."))

        previous_state = self._get_go_back_state()
        current_state_label = dict(self._fields['state'].selection)[self.state]
        previous_state_label = dict(self._fields['state'].selection)[previous_state]

        # Update state and log the reason
        self.write({
            'state': previous_state,
            'stage_change_reason': reason
        })

        # Post message in chatter
        self.message_post(
            body=_("Stage changed back from <b>%s</b> to <b>%s</b><br/>Reason: %s") % (
                current_state_label, previous_state_label, reason
            ),
            message_type='notification'
        )

        # Handle vehicle state if needed
        if previous_state in ['enquiry', 'quotation', 'followup'] and self.vehicle_id:
            try:
                self.vehicle_id.write({'state': 'active'})
            except:
                _logger.warning("Could not reset vehicle state to active")

    # ACTION METHODS - UPDATED to ensure invoice URL exists at all stages
    def action_quotation(self):
        self.write({'state': 'quotation'})

    def action_followup(self):
        self.write({'state': 'followup'})

    def action_resend_followup_template(self):
        """Manual action to resend followup template"""
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
                    'message': _('Follow-up template resent successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Failed'),
                    'message': _('Failed to resend follow-up template. Check message logs for details.'),
                    'type': 'danger',
                    'sticky': False,
                }
            }
        # Resets flags and sends template
        # Returns success/failure notification

    def action_confirm(self):
        """Set appropriate vehicle state when booking is confirmed"""
        self.write({'state': 'confirmed'})

        # Ensure invoice access token exists (should already exist from enquiry)
        if not self.invoice_access_token:
            self._auto_generate_invoice_access_token()

        # Set payment status to invoiced when confirmed
        if self.payment_status == 'not_invoiced':
            self.payment_status = 'invoiced'

        if self.vehicle_id:
            try:
                self.vehicle_id.write({'state': 'booked'})
            except:
                try:
                    self.vehicle_id.write({'state': 'in_use'})
                except:
                    _logger.warning("Could not update vehicle state. Check available states in simply.fleet.vehicle")

    def action_complete(self):
        """Complete booking and ensure invoice URL is available"""
        self.write({'state': 'completed'})

        # Ensure invoice access token exists (should already exist from enquiry)
        if not self.invoice_access_token:
            self._auto_generate_invoice_access_token()

        # Ensure payment status is at least invoiced
        if self.payment_status == 'not_invoiced':
            self.payment_status = 'invoiced'

        if self.vehicle_id:
            try:
                self.vehicle_id.write({'state': 'active'})
            except:
                _logger.warning("Could not reset vehicle state to active")

    def action_feedback(self):
        self.write({'state': 'feedback'})

    def action_reset_to_enquiry(self):
        self.write({'state': 'enquiry'})
        if self.vehicle_id:
            try:
                self.vehicle_id.write({'state': 'active'})
            except:
                _logger.warning("Could not reset vehicle state to active")

    # Other action methods remain the same...
    def action_assign_driver(self):
        return {
            'name': _('Assign Driver'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.driver.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_booking_id': self.id},
        }

    def action_register_payment(self):
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.payment.register.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_booking_id': self.id, 'default_amount': self.balance_amount},
        }

    def action_view_route(self):
        """Open route in Google Maps"""
        self.ensure_one()
        if self.journey_start_location and self.journey_end_location:
            base_url = "https://www.google.com/maps/dir/"
            url = base_url + f"{self.journey_start_location}/{self.journey_end_location}"

            if self.via_stops:
                stops = self.via_stops.split('\n')
                for stop in stops:
                    if stop.strip():
                        url += f"/{stop.strip()}"

            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }

    # UTILITY METHODS
    @api.model
    def _get_time_options(self):
        """Generate time options in 30-minute intervals with AM/PM format"""
        options = []

        # Add options for AM period (midnight to noon)
        options.append(('12:00 AM', '12:00 AM'))
        options.append(('12:30 AM', '12:30 AM'))

        for hour in range(1, 12):
            options.append((f'{hour:02d}:00 AM', f'{hour:02d}:00 AM'))
            options.append((f'{hour:02d}:30 AM', f'{hour:02d}:30 AM'))

        # Add options for PM period (noon to midnight)
        options.append(('12:00 PM', '12:00 PM'))
        options.append(('12:30 PM', '12:30 PM'))

        for hour in range(1, 12):
            options.append((f'{hour:02d}:00 PM', f'{hour:02d}:00 PM'))
            options.append((f'{hour:02d}:30 PM', f'{hour:02d}:30 PM'))

        return options

    @api.onchange('return_journey_needed')
    def _onchange_return_journey(self):
        """Clear return journey fields when return journey is not needed"""
        if not self.return_journey_needed:
            self.return_journey_date = False
            self.return_journey_time = False

    @api.onchange('return_journey_needed', 'journey_start_date', 'return_journey_date')
    def _onchange_return_journey_date(self):
        if self.return_journey_needed and self.journey_start_date and self.return_journey_date:
            if self.return_journey_date < self.journey_start_date:
                return {'warning': {
                    'title': _("Invalid Return Date"),
                    'message': _("Return journey date cannot be earlier than outbound journey date.")
                }}

    # REMOVED: Manual generate invoice action - now automatic
    # def action_generate_invoice(self): - This is now handled automatically

    # UPDATED: View invoice - now opens shareable URL
    def action_view_invoice(self):
        """View the invoice via shareable URL"""
        self.ensure_one()

        # Generate token if not exists
        if not self.invoice_access_token:
            self._auto_generate_invoice_access_token()

        return {
            'type': 'ir.actions.act_url',
            'url': self.invoice_url,
            'target': 'new',
        }

    # UPDATED: Share invoice URL instead of download
    def action_download_invoice(self):
        """Get shareable invoice URL"""
        self.ensure_one()

        # Generate token if not exists
        if not self.invoice_access_token:
            self._auto_generate_invoice_access_token()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invoice URL Generated'),
                'message': _('Shareable URL: %s') % self.invoice_url,
                'type': 'success',
            }
        }

    # NEW: Action to copy invoice URL to clipboard
    def action_copy_invoice_url(self):
        """Copy invoice URL to clipboard"""
        self.ensure_one()

        # Generate token if not exists
        if not self.invoice_access_token:
            self._auto_generate_invoice_access_token()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invoice URL Ready'),
                'message': _('Copy this URL to share: %s') % self.invoice_url,
                'type': 'info',
            }
        }

    # NEW: Action to send invoice URL via email
    def action_email_invoice_url(self):
        """Send invoice URL via email"""
        self.ensure_one()

        # Generate token if not exists
        if not self.invoice_access_token:
            self._auto_generate_invoice_access_token()

        # Create email template context
        template_ctx = {
            'booking_name': self.name,
            'customer_name': self.customer_id.name,
            'invoice_url': self.invoice_url,
            'total_amount': self.total_price,
        }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Invoice URL'),
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'fleet.booking',
                'default_res_id': self.id,
                'default_use_template': False,
                'default_partner_ids': [(6, 0, [self.customer_id.id])],
                'default_subject': _('Invoice for Booking %s') % self.name,
                'default_body': _(
                    'Dear %s,<br/><br/>'
                    'Please find your invoice for booking %s.<br/>'
                    'You can view your invoice by clicking the link below:<br/><br/>'
                    '<a href="%s" target="_blank" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Invoice</a><br/><br/>'
                    'Total Amount: %s<br/><br/>'
                    'Thank you for your business!<br/>'
                    'Best regards,<br/>'
                    '%s'
                ) % (
                                    self.customer_id.name,
                                    self.name,
                                    self.invoice_url,
                                    self.total_price,
                                    self.company_id.name
                                ),
            },
        }


# NEW: Wizard for Booking Cancellation
class FleetBookingCancelWizard(models.TransientModel):
    _name = 'fleet.booking.cancel.wizard'
    _description = 'Fleet Booking Cancel Wizard'

    booking_id = fields.Many2one('fleet.booking', string='Booking', required=True)
    total_amount = fields.Monetary(string='Total Amount', currency_field='currency_id', readonly=True)
    paid_amount = fields.Monetary(string='Paid Amount', currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.company.currency_id)

    # Mandatory cancellation reason
    cancellation_reason = fields.Text(string='Cancellation Reason', required=True,
                                      help='Please provide a detailed reason for cancelling this booking')

    # Refund Policy
    refund_policy = fields.Selection([
        ('full_refund', 'Full Refund'),
        ('partial_refund', 'Partial Refund'),
        ('no_refund', 'No Refund'),
    ], string='Refund Policy', required=True, default='no_refund')

    refund_amount = fields.Monetary(string='Refund Amount', currency_field='currency_id')
    refund_percentage = fields.Float(string='Refund Percentage (%)', digits=(5, 2))
    refund_notes = fields.Text(string='Refund Notes',
                               help='Additional notes about the refund policy or calculation')

    @api.onchange('refund_policy')
    def _onchange_refund_policy(self):
        """Set default refund amount based on policy"""
        if self.refund_policy == 'full_refund':
            self.refund_amount = self.paid_amount
            self.refund_percentage = 100.0
        elif self.refund_policy == 'no_refund':
            self.refund_amount = 0.0
            self.refund_percentage = 0.0
        else:  # partial_refund
            self.refund_amount = 0.0
            self.refund_percentage = 0.0

    @api.onchange('refund_percentage')
    def _onchange_refund_percentage(self):
        """Calculate refund amount from percentage"""
        if self.refund_percentage and self.paid_amount:
            self.refund_amount = (self.refund_percentage / 100.0) * self.paid_amount

    @api.onchange('refund_amount')
    def _onchange_refund_amount(self):
        """Calculate refund percentage from amount"""
        if self.refund_amount and self.paid_amount:
            self.refund_percentage = (self.refund_amount / self.paid_amount) * 100.0

    @api.constrains('refund_amount', 'paid_amount')
    def _check_refund_amount(self):
        """Validate refund amount"""
        for record in self:
            if record.refund_amount > record.paid_amount:
                raise ValidationError(_("Refund amount cannot be greater than the paid amount."))
            if record.refund_amount < 0:
                raise ValidationError(_("Refund amount cannot be negative."))

    def action_confirm_cancellation(self):
        """Confirm booking cancellation"""
        self.ensure_one()

        if not self.cancellation_reason:
            raise UserError(_("Cancellation reason is mandatory."))

        # Validate refund details
        if self.refund_policy == 'partial_refund' and self.refund_amount <= 0:
            raise UserError(_("Please specify the refund amount for partial refund."))

        self.booking_id.cancel_booking_with_details(
            reason=self.cancellation_reason,
            refund_policy=self.refund_policy,
            refund_amount=self.refund_amount,
            refund_percentage=self.refund_percentage,
            refund_notes=self.refund_notes
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Booking Cancelled'),
                'message': _('Booking has been cancelled successfully.'),
                'type': 'warning',
            }
        }


# NEW: Wizard for Processing Refund
class FleetBookingRefundWizard(models.TransientModel):
    _name = 'fleet.booking.refund.wizard'
    _description = 'Fleet Booking Refund Wizard'

    booking_id = fields.Many2one('fleet.booking', string='Booking', required=True)
    refund_amount = fields.Monetary(string='Refund Amount', currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.company.currency_id)

    refund_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card Reversal'),
        ('adjustment', 'Account Adjustment'),
        ('other', 'Other'),
    ], string='Refund Method', required=True)

    refund_notes = fields.Text(string='Processing Notes',
                               help='Additional notes about the refund processing')

    def action_process_refund(self):
        """Process the refund"""
        self.ensure_one()

        self.booking_id.process_refund_with_details(
            refund_method=self.refund_method,
            refund_notes=self.refund_notes
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Refund Processed'),
                'message': _('Refund has been processed successfully.'),
                'type': 'success',
            }
        }


# NEW: Wizard for Go Back One Stage functionality
class FleetBookingGoBackWizard(models.TransientModel):
    _name = 'fleet.booking.go.back.wizard'
    _description = 'Fleet Booking Go Back Wizard'

    booking_id = fields.Many2one('fleet.booking', string='Booking', required=True)
    current_state = fields.Char(string='Current Stage', readonly=True)
    previous_state = fields.Char(string='Previous Stage', readonly=True)
    reason = fields.Text(string='Reason for Going Back', required=True,
                         help='Please provide a reason for going back to the previous stage.')

    def action_confirm_go_back(self):
        """Confirm going back to previous stage"""
        self.ensure_one()
        if not self.reason:
            raise UserError(_("Reason is mandatory."))

        self.booking_id.go_back_with_reason(self.reason)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Stage Changed'),
                'message': _('Booking stage has been moved back successfully.'),
                'type': 'success',
            }
        }


# Extension of res.partner to add booking relationship
class ResPartner(models.Model):
    _inherit = 'res.partner'

    booking_ids = fields.One2many('fleet.booking', 'customer_id', string='Fleet Bookings')

    fleet_booking_count = fields.Integer(
        string='Fleet Booking Count',
        compute='_compute_fleet_booking_count',
        store=False
    )

    @api.depends('booking_ids')
    def _compute_fleet_booking_count(self):
        """Compute fleet booking count for this partner"""
        for partner in self:
            partner.fleet_booking_count = len(partner.booking_ids)

    def action_view_fleet_bookings(self):
        """Action to view fleet bookings for this partner"""
        self.ensure_one()
        return {
            'name': _('Fleet Bookings'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.booking',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
        }


# Extension of hr.employee to add booking relationship
class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    driver_booking_ids = fields.One2many('fleet.booking', 'driver_id', string='Driver Bookings')

    fleet_booking_count = fields.Integer(
        string='Fleet Booking Count',
        compute='_compute_fleet_booking_count',
        store=False
    )

    @api.depends('driver_booking_ids')
    def _compute_fleet_booking_count(self):
        """Compute fleet booking count for this employee as driver"""
        for employee in self:
            employee.fleet_booking_count = len(employee.driver_booking_ids)

    def action_view_fleet_bookings(self):
        """Action to view fleet bookings where this employee is the driver"""
        self.ensure_one()
        return {
            'name': _('Fleet Bookings as Driver'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.booking',
            'view_mode': 'tree,form',
            'domain': [('driver_id', '=', self.id)],
            'context': {'default_driver_id': self.id},
        }


# Terms and Conditions Template Model
class FleetBookingTermsTemplate(models.Model):
    _name = 'fleet.booking.terms.template'
    _description = 'Fleet Booking Terms and Conditions Templates'
    _order = 'sequence, name'

    name = fields.Char(string='Template Name', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    template_content = fields.Html(string='Template Content', required=True)

    @api.model
    def create_default_templates(self):
        """Create default terms and conditions templates"""
        default_templates = [
            {
                'name': 'Standard Terms',
                'sequence': 1,
                'template_content': '''
                <h5>Standard Terms and Conditions</h5>
                <ol>
                    <li><strong>Booking Confirmation:</strong> Your booking is confirmed upon receipt of payment.</li>
                    <li><strong>Cancellation Policy:</strong> 24 hours notice required for cancellations.</li>
                    <li><strong>Payment Terms:</strong> Full payment required before service.</li>
                    <li><strong>Vehicle Maintenance:</strong> All vehicles are regularly serviced and maintained.</li>
                    <li><strong>Driver Responsibility:</strong> All our drivers are licensed and insured.</li>
                </ol>
                '''
            },
        ]

        for template_data in default_templates:
            existing = self.search([('name', '=', template_data['name'])], limit=1)
            if not existing:
                self.create(template_data)