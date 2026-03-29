# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BusCategory(models.Model):
    _name = 'bus.category'
    _description = 'Bus Category'
    _order = 'sequence, name'

    name = fields.Char('Category Name', required=True)
    sequence = fields.Integer('Sequence', default=10)
    description = fields.Text('Description')
    image = fields.Binary('Category Image')
    active = fields.Boolean('Active', default=True)


class BusFleet(models.Model):
    _name = 'bus.fleet'
    _description = 'Bus Fleet Management'
    _order = 'name'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Bus Name/Number', required=True)
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    category_id = fields.Many2one('bus.category', 'Category', required=True)
    seating_capacity = fields.Integer('Seating Capacity', required=True)
    vehicle_number = fields.Char('Vehicle Number', required=True)

    # Bus Features
    is_ac = fields.Boolean('AC Available', default=True)
    has_wifi = fields.Boolean('WiFi Available')
    has_music_system = fields.Boolean('Music System')
    has_tv = fields.Boolean('TV/Entertainment')
    has_charging_point = fields.Boolean('Charging Points')
    has_washroom = fields.Boolean('Washroom')
    pushback_seats = fields.Boolean('Push Back Seats')
    reading_lights = fields.Boolean('Reading Lights')

    # Status and Pricing
    state = fields.Selection([
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive')
    ], string='Status', default='available', required=True)

    daily_rate = fields.Float('Daily Rate (Rs.)', required=True)
    per_km_rate = fields.Float('Per KM Rate (Rs.)')

    # Additional Information
    driver_id = fields.Many2one('res.partner', 'Primary Driver',
                                domain=[('is_company', '=', False)])
    conductor_id = fields.Many2one('res.partner', 'Conductor',
                                   domain=[('is_company', '=', False)])
    manufacture_year = fields.Integer('Manufacture Year')
    insurance_expiry = fields.Date('Insurance Expiry')
    permit_expiry = fields.Date('Permit Expiry')
    fitness_expiry = fields.Date('Fitness Certificate Expiry')

    description = fields.Text('Description')
    image = fields.Binary('Bus Image')
    images = fields.One2many('bus.fleet.image', 'bus_id', 'Additional Images')

    # Booking relation
    booking_ids = fields.One2many('bus.booking', 'bus_id', 'Bookings')
    booking_count = fields.Integer('Booking Count', compute='_compute_booking_count')

    active = fields.Boolean('Active', default=True)

    # VIDEO FIELDS - MP4 Support
    video_file = fields.Binary('Video File (MP4)', help="Upload MP4 video file for bus showcase")
    video_filename = fields.Char('Video Filename')
    has_video = fields.Boolean('Has Video', compute='_compute_has_video', store=True)

    # YouTube Video (keeping existing field for backward compatibility)
    youtube_video_url = fields.Char('YouTube Video URL', help="YouTube video URL for bus showcase")
    video_thumbnail = fields.Binary('Video Thumbnail')

    # NEW FIELDS - Detailed Specifications
    engine_type = fields.Char('Engine Type', default='BS6 Diesel Engine, 6-cylinder, Turbo')
    power_output = fields.Char('Power Output', default='220 HP @ 2400 RPM')
    transmission = fields.Selection([
        ('manual', '6-Speed Manual'),
        ('amt', '6-Speed AMT'),
        ('automatic', 'Automatic')
    ], string='Transmission', default='manual')
    fuel_capacity = fields.Float('Fuel Tank Capacity (Liters)', default=300)
    mileage = fields.Char('Mileage', default='8-10 km/l')
    overall_length = fields.Float('Overall Length (meters)', default=12.0)
    overall_width = fields.Float('Overall Width (meters)', default=2.5)
    overall_height = fields.Float('Overall Height (meters)', default=3.4)
    ground_clearance = fields.Integer('Ground Clearance (mm)', default=230)
    suspension_type = fields.Char('Suspension', default='Air suspension with auto-leveling')
    braking_system = fields.Char('Braking System', default='Air brakes with ABS')

    # NEW FIELDS - Advanced Comfort Features
    multi_zone_ac = fields.Boolean('Multi-Zone AC', default=True)
    air_purification = fields.Boolean('Air Purification System')
    humidity_control = fields.Boolean('Humidity Control')
    ergonomic_seats = fields.Boolean('Ergonomic Leather Seats', default=True)
    adjustable_headrests = fields.Boolean('Adjustable Headrests', default=True)
    seat_belts = fields.Boolean('Individual Seat Belts', default=True)
    extra_legroom = fields.Boolean('Extra Legroom Design', default=True)

    # NEW FIELDS - Lighting System
    led_ambient_lighting = fields.Boolean('LED Ambient Lighting', default=True)
    individual_reading_lights = fields.Boolean('Individual Reading Lights', default=True)
    step_lighting = fields.Boolean('Step Lighting')
    emergency_lighting = fields.Boolean('Emergency Lighting System', default=True)
    mood_lighting = fields.Boolean('Mood Lighting Options')

    # NEW FIELDS - Refreshment Features
    mini_refrigerator = fields.Boolean('Mini Refrigerator')
    refrigerator_capacity = fields.Integer('Refrigerator Capacity (Liters)', default=80)
    water_dispenser = fields.Boolean('Water Dispenser')
    cup_holders = fields.Boolean('Cup Holders', default=True)
    waste_disposal = fields.Boolean('Waste Disposal System')

    # NEW FIELDS - Entertainment System
    led_tv_screens = fields.Boolean('LED TV Screens')
    tv_screen_size = fields.Char('TV Screen Size', default='32 inch')
    dvd_player = fields.Boolean('DVD/USB Media Player')
    surround_sound = fields.Boolean('Surround Sound System')
    wireless_microphone = fields.Boolean('Wireless Microphone')
    bluetooth_connectivity = fields.Boolean('Bluetooth Connectivity')

    # NEW FIELDS - Charging and Connectivity
    usb_charging_ports = fields.Boolean('USB Charging Ports', default=True)
    power_outlets_230v = fields.Boolean('230V Power Outlets')
    mobile_holders = fields.Boolean('Mobile Phone Holders')
    wireless_charging = fields.Boolean('Wireless Charging Pads')
    power_backup = fields.Boolean('Power Backup System')
    wifi_hotspot = fields.Boolean('WiFi Hotspot')
    gps_navigation = fields.Boolean('GPS Navigation', default=True)
    real_time_tracking = fields.Boolean('Real-time Tracking', default=True)
    digital_display = fields.Boolean('Digital Display Boards')
    pa_system = fields.Boolean('PA System')

    # NEW FIELDS - Safety Systems
    abs_ebd = fields.Boolean('ABS with EBD', default=True)
    speed_limiting = fields.Boolean('Speed Limiting Device', default=True)
    driver_fatigue_monitor = fields.Boolean('Driver Fatigue Monitor')
    hill_start_assist = fields.Boolean('Hill Start Assist')
    emergency_braking = fields.Boolean('Emergency Braking System')

    # NEW FIELDS - Emergency Equipment
    fire_extinguisher = fields.Boolean('Fire Extinguisher', default=True)
    first_aid_kit = fields.Boolean('First Aid Kit', default=True)
    emergency_exits = fields.Boolean('Emergency Exits', default=True)
    emergency_hammer = fields.Boolean('Emergency Hammer', default=True)
    warning_triangles = fields.Boolean('Reflective Warning Triangles', default=True)

    # NEW FIELDS - Security Features
    cctv_surveillance = fields.Boolean('CCTV Surveillance System')
    gps_tracking_security = fields.Boolean('GPS Tracking (Security)')
    anti_theft_alarm = fields.Boolean('Anti-theft Alarm')
    central_locking = fields.Boolean('Central Locking System')
    panic_button = fields.Boolean('Panic Button')

    # NEW FIELDS - Rating and Reviews (Simple fields, no computation)
    average_rating = fields.Float('Average Rating', default=5.0)
    review_count = fields.Integer('Review Count', default=0)
    price_range_min = fields.Float('Price Range Min')
    price_range_max = fields.Float('Price Range Max')

    @api.depends('name', 'vehicle_number')
    def _compute_display_name(self):
        for bus in self:
            bus.display_name = f"{bus.name} ({bus.vehicle_number})"

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for bus in self:
            bus.booking_count = len(bus.booking_ids)

    @api.depends('video_file', 'youtube_video_url')
    def _compute_has_video(self):
        for bus in self:
            bus.has_video = bool(bus.video_file or bus.youtube_video_url)

    @api.constrains('seating_capacity')
    def _check_seating_capacity(self):
        for bus in self:
            if bus.seating_capacity <= 0:
                raise ValidationError(_('Seating capacity must be greater than 0.'))

    @api.constrains('daily_rate', 'per_km_rate')
    def _check_rates(self):
        for bus in self:
            if bus.daily_rate < 0:
                raise ValidationError(_('Daily rate cannot be negative.'))
            if bus.per_km_rate < 0:
                raise ValidationError(_('Per KM rate cannot be negative.'))

    def action_view_bookings(self):
        return {
            'name': _('Bookings'),
            'domain': [('bus_id', '=', self.id)],
            'view_type': 'form',
            'res_model': 'bus.booking',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'context': {'default_bus_id': self.id}
        }

    def action_set_available(self):
        self.write({'state': 'available'})

    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})

    def get_youtube_video_id(self):
        """Extract YouTube video ID from URL"""
        if not self.youtube_video_url:
            return None

        import re
        youtube_regex = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
        match = re.search(youtube_regex, self.youtube_video_url)
        return match.group(1) if match else None

    def get_youtube_thumbnail_url(self):
        """Get YouTube thumbnail URL"""
        video_id = self.get_youtube_video_id()
        if video_id:
            return f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
        return None

    def get_youtube_embed_url(self):
        """Get YouTube embed URL"""
        video_id = self.get_youtube_video_id()
        if video_id:
            return f'https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1'
        return None

    def get_video_url(self):
        """Get video URL for MP4 file"""
        if self.video_file:
            return f'/web/content/bus.fleet/{self.id}/video_file/{self.video_filename or "bus_video.mp4"}'
        return None


class BusFleetImage(models.Model):
    _name = 'bus.fleet.image'
    _description = 'Bus Fleet Images'

    name = fields.Char('Image Name')
    image = fields.Binary('Image', required=True)
    bus_id = fields.Many2one('bus.fleet', 'Bus', required=True, ondelete='cascade')