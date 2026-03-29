from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import pytz
import logging

_logger = logging.getLogger(__name__)

class SimplyFleetFuelLog(models.Model):
    _name = 'simply.fleet.fuel.log'
    _description = 'Fuel Log'
    _inherit = ['mail.thread']  # Removed 'mail.activity.mixin' to disable activities
    _order = 'datetime desc, id desc'  # Changed from 'date desc' to 'datetime desc'

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Fuel log reference must be unique!')
    ]

    name = fields.Char(string='Reference', readonly=True, copy=False)
    vehicle_root = fields.Char(related='vehicle_id.vehicle_root', string='Vehicle Root', readonly=True, store=True)
    vehicle_id = fields.Many2one(
        'simply.fleet.vehicle',
        string='Vehicle',
        required=True,
        tracking=True,
        ondelete='restrict',
        index=True
    )

    # Add new field to get vehicle type code
    vehicle_type_code = fields.Char(
        string='Vehicle Type Code',
        compute='_compute_vehicle_type_code',
        store=True,
        help='Code of the vehicle type (bus, car, etc.) for icon display'
    )

    # Add related fields for vehicle min and max mileage
    vehicle_min_mileage = fields.Float(
        string='Min Mileage',
        related='vehicle_id.min_mileage',
        store=True
    )

    vehicle_max_mileage = fields.Float(
        string='Max Mileage',
        related='vehicle_id.max_mileage',
        store=True
    )

    # Add Currency Field
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id,
        required=True
    )

    # Add DateTime field for date and time
    datetime = fields.Datetime(
        string='Date & Time',
        required=True,
        default=fields.Datetime.now,  # Auto-selects current date and time
        tracking=True
    )

    # Keep date field as computed for compatibility
    date = fields.Date(
        string='Date',
        compute='_compute_date',
        store=True,
        tracking=True
    )
    # Add datetime_display field
    datetime_display = fields.Char(
        string='Formatted Date & Time',
        compute='_compute_display_date',
        store=True,
        help='Formatted datetime for display purposes'
    )

    # Add display date computed field
    display_date = fields.Date(
        string='Display Date',
        compute='_compute_display_date',
        store=True
    )
    time_display = fields.Char(
        string='Time',
        compute='_compute_time_display',
        store=True,
        help='Time portion of the datetime field'
    )

    show_transaction_type = fields.Boolean(
        compute='_compute_show_transaction_type',
        store=True
    )

    transaction_type_id = fields.Many2one(
        'simply.fleet.transaction.type',
        string='Transaction Type',
        ondelete='restrict',
        tracking=True
    )

    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        readonly=True,
        default=lambda self: self.env.user.id,
        ondelete='restrict',
        tracking=True
    )

    previous_odometer = fields.Float(
        string='Previous Odometer',
        compute='_compute_previous_odometer',
        store=True,
        tracking=True
    )

    distance_travelled = fields.Float(
        string='Distance Travelled (km)',
        compute='_compute_distance_travelled',
        store=True,
        tracking=True
    )

    show_mileage = fields.Boolean(
        compute='_compute_show_mileage',
        store=True
    )

    mileage = fields.Float(
        string='Mileage (km/l)',
        compute='_compute_mileage',
        store=True,
        tracking=True,
        help='Vehicle mileage in kilometers per liter'
    )

    fill_type = fields.Selection([
        ('full', 'Full Tank'),
        ('partial', 'Partial Fill')
    ], string='Fill Type', required=True, default='full', tracking=True)

    fuel_type = fields.Selection([
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('cng', 'CNG'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid')
    ], string='Fuel Type', required=True, tracking=True)

    station_type = fields.Selection([
        ('diesel_tanker', 'Diesel Tanker'),
        ('petrol_pump', 'Petrol Pump')
    ], string='Station Type', required=True, tracking=True)

    liters = fields.Float(
        string='Quantity',
        tracking=True,
        required=True,
        help='Fuel quantity in liters'
    )

    # Update to Monetary field
    price_per_liter = fields.Monetary(
        string='Price per Liter',
        tracking=True,
        required=True,
        currency_field='currency_id'
    )

    # Update to Monetary field
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        currency_field='currency_id'
    )

    odometer = fields.Float(
        string='Odometer Reading',
        tracking=True,
        required=True
    )

    notes = fields.Text(string='Notes')

    # New display fields for showing values with units
    liters_display = fields.Char(
        string='Quantity',
        compute='_compute_display_fields',
        store=True
    )

    odometer_display = fields.Char(
        string='Odometer Reading',
        compute='_compute_display_fields',
        store=True
    )

    previous_odometer_display = fields.Char(
        string='Previous Odometer',
        compute='_compute_display_fields',
        store=True
    )

    distance_travelled_display = fields.Char(
        string='Distance Travelled',
        compute='_compute_display_fields',
        store=True
    )

    mileage_display = fields.Char(
        string='Mileage',
        compute='_compute_display_fields',
        store=True
    )

    driver_id = fields.Many2one(
        'hr.employee',
        string='Driver',
    	required=True,  # Add this line
        tracking=True,
        domain=[('job_title', 'ilike', 'driver')],
        help='Assigned driver for this vehicle'
    )

    # ===== NEW FIELDS FOR ODOMETER REPLACEMENT/REVERSAL =====
    is_odometer_replaced = fields.Boolean(
        string='Odometer Replaced/Reversed',
        default=False,
        tracking=True,
        help='Check this if the odometer has been replaced or reversed'
    )

    odometer_replacement_reason = fields.Selection([
        ('replaced', 'Meter Replaced'),
        ('reversed', 'Meter Reversed/Damaged'),
        ('other', 'Other')
    ], string='Replacement Reason', tracking=True)

    odometer_replacement_notes = fields.Text(
        string='Replacement Notes',
        help='Additional notes about the odometer replacement/reversal'
    )

    show_odometer_replacement_warning = fields.Boolean(
        string='Show Replacement Warning',
        compute='_compute_show_odometer_replacement_warning',
        help='Shows warning when odometer reading is significantly lower than previous'
    )
    # ===== END NEW FIELDS =====

    # === METHODS TO DISABLE LOG NOTE FUNCTIONALITY ===

    def _track_subtype(self, init_values):
        """Override to disable automatic message posting"""
        return False

    def _message_get_suggested_recipients(self):
        """Override to control suggested recipients"""
        recipients = super()._message_get_suggested_recipients()
        return recipients

    @api.model
    def message_post(self, **kwargs):
        """Override message_post to block manual log notes"""
        # Block manual log notes (those without mail_post_autofollow context)
        if not self.env.context.get('mail_post_autofollow') and not self.env.context.get('mail_create_nolog'):
            # Check if this is a system message (automatic)
            message_type = kwargs.get('message_type', 'notification')
            subtype_xmlid = kwargs.get('subtype_xmlid', '')

            # Allow only system messages and notifications
            if message_type == 'comment' and not subtype_xmlid:
                # This is likely a manual log note, block it
                return self.env['mail.message']

        return super().message_post(**kwargs)

    def _message_post_after_hook(self, message, msg_vals):
        """Override to prevent certain message types"""
        # Only call super for system messages
        if msg_vals.get('message_type') != 'comment':
            return super()._message_post_after_hook(message, msg_vals)
        return message

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        """Override to control notifications"""
        # Only notify for system messages, not manual log notes
        if msg_vals and msg_vals.get('message_type') == 'comment':
            return
        return super()._notify_thread(message, msg_vals, **kwargs)

    @api.model
    def _message_compute_author(self, author_id=None, email_from=None, raise_on_email=True):
        """Override to control message authoring - Fixed for Odoo 17"""
        return super()._message_compute_author(author_id, email_from, raise_on_email=raise_on_email)

    def _message_add_suggested_recipient(self, result, partner=None, email=None, lang=None, reason=''):
        """Override to control suggested recipients"""
        # Disable suggested recipients for manual messages
        if not self.env.context.get('mail_post_autofollow'):
            return result
        return super()._message_add_suggested_recipient(result, partner, email, lang, reason)

    # === END DISABLE LOG NOTE FUNCTIONALITY ===

    # Handle data migration during module upgrade
    @api.model
    def _init_column(self, column_name):
        """ Initialize datetime field based on existing date field during installation """
        result = super()._init_column(column_name)

        if column_name == 'datetime':
            # Only execute if we're initializing the datetime column
            query = """
                UPDATE simply_fleet_fuel_log 
                SET datetime = date + interval '12 hours'
                WHERE datetime IS NULL AND date IS NOT NULL
            """
            self.env.cr.execute(query)

        return result

    # ===== NEW METHOD: Check if odometer replacement warning should be shown =====
    @api.depends('odometer', 'previous_odometer', 'is_odometer_replaced')
    def _compute_show_odometer_replacement_warning(self):
        """Show warning when odometer reading goes backwards by more than 25000 km"""
        for record in self:
            if record.is_odometer_replaced:
                # If already marked as replaced, don't show warning
                record.show_odometer_replacement_warning = False
            elif record.previous_odometer and record.odometer:
                # Show warning if odometer decreased by more than 25000 km
                difference = record.previous_odometer - record.odometer
                record.show_odometer_replacement_warning = difference > 25000
            else:
                record.show_odometer_replacement_warning = False
    # ===== END NEW METHOD =====

    # NEW METHOD: Update chronological chain of fuel logs
    def _update_chronological_chain(self, vehicle_id):
        """Update previous_odometer for all fuel logs of a vehicle in chronological order"""
        if not vehicle_id:
            return

        # Prevent recursion by checking if we're already updating this vehicle
        if hasattr(self.env, '_chain_update_in_progress'):
            if vehicle_id in self.env._chain_update_in_progress:
                return
        else:
            self.env._chain_update_in_progress = set()

        # Mark this vehicle as being updated
        self.env._chain_update_in_progress.add(vehicle_id)

        try:
            # Get all fuel logs for this vehicle ordered by datetime
            fuel_logs = self.env['simply.fleet.fuel.log'].search([
                ('vehicle_id', '=', vehicle_id),
                ('odometer', '>', 0)
            ], order='datetime asc, id asc')

            if not fuel_logs:
                return

            # Get vehicle's initial odometer
            vehicle = self.env['simply.fleet.vehicle'].browse(vehicle_id)
            initial_odometer = vehicle.initial_odometer if vehicle.initial_odometer else 0.0

            previous_reading = initial_odometer

            # Update each log in chronological order using direct SQL to avoid recursion
            for log in fuel_logs:
                # ===== MODIFIED: Handle odometer replacement/reversal =====
                if log.is_odometer_replaced:
                    # If odometer was replaced/reversed, use 0 as previous reading
                    # This resets the chain for this entry
                    distance_travelled = 0.0
                    mileage = 0.0

                    # Update the record
                    self.env.cr.execute("""
                        UPDATE simply_fleet_fuel_log 
                        SET previous_odometer = %s,
                            distance_travelled = %s,
                            mileage = %s
                        WHERE id = %s
                    """, (0.0, distance_travelled, mileage, log.id))

                    # Set current odometer as the new baseline for next entries
                    previous_reading = log.odometer
                else:
                    # Normal processing - calculate distance travelled
                    distance_travelled = max(0, log.odometer - previous_reading) if log.odometer > 0 else 0.0

                    # Calculate mileage if this is a full tank fill
                    mileage = 0.0
                    if log.fill_type == 'full' and log.liters and log.liters > 0 and distance_travelled > 0:
                        mileage = distance_travelled / log.liters

                    # Update all fields at once with direct SQL
                    self.env.cr.execute("""
                        UPDATE simply_fleet_fuel_log 
                        SET previous_odometer = %s,
                            distance_travelled = %s,
                            mileage = %s
                        WHERE id = %s
                    """, (previous_reading, distance_travelled, mileage, log.id))

                    # Set the previous reading for the next log
                    previous_reading = log.odometer
                # ===== END MODIFICATION =====

            # Invalidate cache for the updated fields
            fuel_logs.invalidate_recordset(['previous_odometer', 'distance_travelled', 'mileage'])

            # Force recomputation of display fields only (these don't trigger writes)
            for log in fuel_logs:
                log._compute_display_fields()

        finally:
            # Remove this vehicle from the update set
            self.env._chain_update_in_progress.discard(vehicle_id)

    # Compute date from datetime for compatibility
    @api.depends('datetime')
    def _compute_date(self):
        for record in self:
            if record.datetime:
                record.date = record.datetime.date()
            else:
                record.date = False

    @api.depends('datetime')
    def _compute_time_display(self):
        for record in self:
            if record.datetime:
                # Format the time as HH:MM:SS (fixed: removed extra colon)
                record.time_display = record.datetime.strftime('%H:%M:%S')
            else:
                record.time_display = False  # Fixed spelling of False

    # Compute method for display fields with units
    @api.depends('liters', 'odometer', 'previous_odometer', 'distance_travelled', 'mileage')
    def _compute_display_fields(self):
        for record in self:
            # Format with units (handle zero and None values)
            record.liters_display = f"{record.liters} L" if record.liters else "0 L"
            record.odometer_display = f"{int(record.odometer)} km" if record.odometer else "0 km"
            record.previous_odometer_display = f"{int(record.previous_odometer)} km" if record.previous_odometer else "0 km"
            record.distance_travelled_display = f"{int(record.distance_travelled)} km" if record.distance_travelled else "0 km"

            # Only show mileage for full tank fills
            if record.fill_type == 'full' and record.mileage:
                record.mileage_display = f"{round(record.mileage, 2)} km/L"
            else:
                record.mileage_display = "0 km/L"

    # New compute method for vehicle type code
    @api.depends('vehicle_id', 'vehicle_id.vehicle_type_id', 'vehicle_id.vehicle_type_id.code')
    def _compute_vehicle_type_code(self):
        for record in self:
            if record.vehicle_id and record.vehicle_id.vehicle_type_id and record.vehicle_id.vehicle_type_id.code:
                record.vehicle_type_code = record.vehicle_id.vehicle_type_id.code
            else:
                record.vehicle_type_code = 'car'  # Default to car if no type code found

    @api.depends('datetime')
    def _compute_display_date(self):
        for record in self:
            if record.datetime:
                # Get the user's timezone
                user_tz = self.env.user.tz or 'UTC'
                try:
                    # Convert to user's timezone for display purposes
                    dt_as_utc = pytz.UTC.localize(record.datetime.replace(tzinfo=None)) if not record.datetime.tzinfo else record.datetime
                    local_dt = dt_as_utc.astimezone(pytz.timezone(user_tz))

                    # Set both date and time using the timezone-converted datetime
                    # This ensures the date is correct in the user's timezone
                    record.display_date = local_dt.date()
                    record.datetime_display = local_dt.strftime('%I:%M %p')
                except Exception as e:
                    _logger.error(f"Timezone conversion error: {e}")
                    # Fallback to UTC if conversion fails
                    record.display_date = record.datetime.date()
                    record.datetime_display = record.datetime.strftime('%I:%M %p')
            else:
                record.display_date = False
                record.datetime_display = False

    @api.depends('fill_type')
    def _compute_show_mileage(self):
        for record in self:
            record.show_mileage = bool(record.fill_type == 'full')

    @api.onchange('fill_type')
    def _onchange_fill_type(self):
        for record in self:
            if record.fill_type == 'partial':
                record.mileage = False

    @api.depends('station_type')
    def _compute_show_transaction_type(self):
        for record in self:
            # Always hide the transaction type field regardless of station type
            record.show_transaction_type = False

    # Removed the onchange_station_type method as it's no longer needed

    # ===== MODIFIED: Updated mileage computation to include partial fills =====
    @api.depends('distance_travelled', 'liters', 'fill_type', 'vehicle_id', 'datetime')
    def _compute_mileage(self):
        for record in self:
            if record.fill_type == 'full' and record.liters and record.liters > 0:
                # For full tank, accumulate fuel and distance from previous partial fills
                total_fuel = record.liters
                total_distance = record.distance_travelled or 0.0

                if record.vehicle_id and record.datetime:
                    # Find all partial fills since the last full tank
                    # Search for logs between the previous full tank and this one
                    previous_full_tank = self.env['simply.fleet.fuel.log'].search([
                        ('vehicle_id', '=', record.vehicle_id.id),
                        ('datetime', '<', record.datetime),
                        ('fill_type', '=', 'full'),
                        ('id', '!=', record._origin.id or False),
                    ], order='datetime desc, id desc', limit=1)

                    # Define the search domain for partial fills
                    domain = [
                        ('vehicle_id', '=', record.vehicle_id.id),
                        ('datetime', '<', record.datetime),
                        ('fill_type', '=', 'partial'),
                        ('id', '!=', record._origin.id or False),
                    ]

                    # If there was a previous full tank, only get partials after it
                    if previous_full_tank:
                        domain.append(('datetime', '>', previous_full_tank.datetime))

                    # Get all partial fills in this range
                    partial_fills = self.env['simply.fleet.fuel.log'].search(
                        domain,
                        order='datetime asc, id asc'
                    )

                    # Accumulate fuel and distance from partial fills
                    for partial in partial_fills:
                        if partial.liters:
                            total_fuel += partial.liters
                        if partial.distance_travelled:
                            total_distance += partial.distance_travelled

                # Calculate mileage with accumulated values
                if total_fuel > 0 and total_distance > 0:
                    record.mileage = total_distance / total_fuel
                else:
                    record.mileage = 0.0
            else:
                record.mileage = 0.0
    # ===== END MODIFIED MILEAGE COMPUTATION =====

    @api.depends('liters', 'price_per_liter')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = (record.liters or 0.0) * (record.price_per_liter or 0.0)

    @api.depends('vehicle_id', 'datetime', 'is_odometer_replaced')
    def _compute_previous_odometer(self):
        for record in self:
            if not record.vehicle_id or not record.vehicle_id.exists():
                record.previous_odometer = 0.0
                continue

            # ===== MODIFIED: Handle odometer replacement =====
            if record.is_odometer_replaced:
                # If odometer is replaced, set previous to 0
                record.previous_odometer = 0.0
                continue
            # ===== END MODIFICATION =====

            try:
                # Find the most recent fuel log for this vehicle with a valid odometer reading
                previous_log = self.env['simply.fleet.fuel.log'].search([
                    ('vehicle_id', '=', record.vehicle_id.id),
                    ('datetime', '<', record.datetime or fields.Datetime.now()),  # Use datetime instead of date
                    ('id', '!=', record._origin.id or False),
                    ('odometer', '>', 0)  # Only consider logs with positive odometer values
                ], order='datetime desc, id desc', limit=1)

                if previous_log and previous_log.exists():
                    record.previous_odometer = previous_log.odometer
                else:
                    # If no previous log exists, use the vehicle's initial odometer or 0
                    record.previous_odometer = record.vehicle_id.initial_odometer if record.vehicle_id.initial_odometer else 0.0
            except Exception as e:
                _logger.error(f"Error computing previous odometer: {e}")
                record.previous_odometer = 0.0

    @api.depends('odometer', 'previous_odometer', 'is_odometer_replaced')
    def _compute_distance_travelled(self):
        for record in self:
            # ===== MODIFIED: Handle odometer replacement =====
            if record.is_odometer_replaced:
                # If odometer is replaced, distance is 0
                record.distance_travelled = 0.0
            elif record.odometer and record.odometer > 0 and record.previous_odometer is not False:
                # Calculate the distance traveled (always non-negative)
                distance = record.odometer - record.previous_odometer
                record.distance_travelled = max(0, distance)  # Ensure non-negative
            else:
                record.distance_travelled = 0.0
            # ===== END MODIFICATION =====

    @api.onchange('vehicle_id', 'datetime')
    def _onchange_vehicle_id(self):
        if not self.vehicle_id or not self.vehicle_id.exists():
            return

        # Update the code to use datetime instead of date
        if self.datetime:
            previous_log = self.env['simply.fleet.fuel.log'].search([
                ('vehicle_id', '=', self.vehicle_id.id),
                ('datetime', '<', self.datetime),
                ('odometer', '>', 0)
            ], order='datetime desc, id desc', limit=1)

            if previous_log and previous_log.exists():
                self.previous_odometer = previous_log.odometer
            else:
                self.previous_odometer = self.vehicle_id.initial_odometer if self.vehicle_id.initial_odometer else 0.0

        if not self.fill_type:
            self.fill_type = 'full'

    # ===== NEW ONCHANGE: Handle odometer replacement checkbox =====
    @api.onchange('is_odometer_replaced')
    def _onchange_is_odometer_replaced(self):
        """When odometer replacement is checked, clear the replacement reason"""
        if not self.is_odometer_replaced:
            self.odometer_replacement_reason = False
            self.odometer_replacement_notes = False
    # ===== END NEW ONCHANGE =====

    # ===== MODIFIED: Enhanced odometer validation with replacement handling =====
    @api.constrains('odometer', 'previous_odometer', 'is_odometer_replaced', 'odometer_replacement_reason')
    def _check_odometer(self):
        for record in self:
            # Check that odometer is provided
            if not record.odometer or record.odometer <= 0:
                raise UserError(_('New odometer reading is required and must be greater than zero'))

            # Skip backward odometer validation if odometer is marked as replaced
            if record.is_odometer_replaced:
                # Ensure replacement reason is provided when marked as replaced
                if not record.odometer_replacement_reason:
                    raise UserError(_(
                        'Please select a reason for the odometer replacement/reversal.'
                    ))
                # Skip all other validations for replaced odometers
                continue

            # Check if odometer went backwards by more than 25000 km
            if record.previous_odometer and record.odometer < record.previous_odometer:
                difference = record.previous_odometer - record.odometer
                
                if difference > 25000:
                    # Show detailed error message with option to mark as replaced
                    raise ValidationError(_(
                        'The new odometer reading (%s km) is %s km less than the previous reading (%s km).\n\n'
                        'If the odometer has been replaced, reversed, or damaged:\n'
                        '1. Check the "Odometer Replaced/Reversed" checkbox\n'
                        '2. Select the appropriate reason\n'
                        '3. Add any relevant notes\n\n'
                        'Otherwise, please verify your odometer reading.'
                    ) % (int(record.odometer), int(difference), int(record.previous_odometer)))
                else:
                    # Normal backward validation for smaller differences
                    raise UserError(_(
                        'New odometer reading (%s km) cannot be less than the previous reading (%s km). '
                        'Please check your odometer reading and ensure it\'s correct.'
                    ) % (int(record.odometer), int(record.previous_odometer)))

            # Optional: Warning for unusually large odometer jumps (more than 2000 km)
            if record.previous_odometer and record.odometer > record.previous_odometer + 2000:
                # This could be a warning instead of an error, depending on your business needs
                pass  # You can implement a warning mechanism here if needed

            # Check if previous odometer is zero (except for first entry)
            if record.previous_odometer == 0:
                # Check if this is really the first log for this vehicle
                previous_logs_count = self.env['simply.fleet.fuel.log'].search_count([
                    ('vehicle_id', '=', record.vehicle_id.id),
                    ('id', '!=', record._origin.id or False),
                ])

                if previous_logs_count > 0:
                    raise UserError(_('Previous odometer cannot be zero except for the first fuel log entry'))
    # ===== END MODIFIED VALIDATION =====

    @api.constrains('liters')
    def _check_fuel_amount(self):
        for record in self:
            if not record.liters:
                raise UserError(_('Quantity is required. Please enter a value.'))
            elif record.liters <= 0:
                raise UserError(_('Quantity must be greater than zero'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Ensure liters is provided in creation
            if 'liters' not in vals or not vals.get('liters'):
                raise UserError(_('Quantity (liters) is a required field.'))

            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('simply.fleet.fuel.log')

        # Create the records first
        records = super().create(vals_list)

        # Update chronological chain for each affected vehicle
        affected_vehicles = set()
        for record in records:
            if record.vehicle_id:
                affected_vehicles.add(record.vehicle_id.id)

        # Update chains for all affected vehicles
        for vehicle_id in affected_vehicles:
            records._update_chronological_chain(vehicle_id)

        return records

    def write(self, vals):
        # Prevent recursion during chain updates
        if hasattr(self.env, '_chain_update_in_progress'):
            # If we're updating within a chain update, just call super and return
            for record in self:
                if record.vehicle_id and record.vehicle_id.id in self.env._chain_update_in_progress:
                    return super().write(vals)

        # Store original vehicle_ids and datetimes before update
        original_data = {}
        affected_vehicles = set()

        for record in self:
            original_data[record.id] = {
                'vehicle_id': record.vehicle_id.id if record.vehicle_id else False,
                'datetime': record.datetime
            }
            if record.vehicle_id:
                affected_vehicles.add(record.vehicle_id.id)

        # Perform the update
        result = super().write(vals)

        # Check if vehicle_id or datetime changed
        for record in self:
            # Add new vehicle to affected list if vehicle changed
            if 'vehicle_id' in vals and record.vehicle_id:
                affected_vehicles.add(record.vehicle_id.id)

        # Update chronological chain for all affected vehicles
        for vehicle_id in affected_vehicles:
            self._update_chronological_chain(vehicle_id)

        return result

    def unlink(self):
        # Store vehicle_ids before deletion
        affected_vehicles = set()
        for record in self:
            if record.vehicle_id:
                affected_vehicles.add(record.vehicle_id.id)

        # Perform deletion
        result = super().unlink()

        # Update chronological chain for affected vehicles
        for vehicle_id in affected_vehicles:
            self._update_chronological_chain(vehicle_id)

        return result
