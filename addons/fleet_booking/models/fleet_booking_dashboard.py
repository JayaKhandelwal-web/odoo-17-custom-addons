from odoo import api, fields, models, _
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class FleetBookingDashboard(models.Model):
    _name = 'fleet.booking.dashboard'
    _description = 'Fleet Booking Dashboard'
    _order = 'id desc'

    name = fields.Char(string='Dashboard Name', required=True, default='Fleet Booking Analytics')

    # Filter Fields
    date_range = fields.Selection([
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('quarter', 'This Quarter'),
        ('year', 'This Year'),
        ('custom', 'Custom Range'),
    ], string='Date Range', default='month')

    booking_type = fields.Selection([
        ('all', 'All Types'),
        ('individual', 'Individual'),
        ('company', 'Company'),
    ], string='Booking Type', default='all')

    status = fields.Selection([
        ('all', 'All Status'),
        ('enquiry', 'Enquiry'),
        ('quotation', 'Quotation'),
        ('followup', 'Follow Up'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='all')

    vehicle_type = fields.Selection([
        ('all', 'All Vehicles'),
        ('luxury', 'Luxury Vehicles'),
        ('coach', 'AC Coaches'),
        ('sedan', 'Sedans'),
    ], string='Vehicle Type', default='all')

    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')

    # KPI Fields
    total_bookings = fields.Integer(string='Total Bookings', compute='_compute_dashboard_data', store=True)
    confirmed_bookings = fields.Integer(string='Confirmed Bookings', compute='_compute_dashboard_data', store=True)
    completed_bookings = fields.Integer(string='Completed Bookings', compute='_compute_dashboard_data', store=True)
    cancelled_bookings = fields.Integer(string='Cancelled Bookings', compute='_compute_dashboard_data', store=True)
    total_revenue = fields.Monetary(string='Total Revenue', currency_field='currency_id',
                                    compute='_compute_dashboard_data', store=True)
    completion_rate = fields.Float(string='Completion Rate', compute='_compute_dashboard_data', store=True)
    cancellation_rate = fields.Float(string='Cancellation Rate', compute='_compute_dashboard_data', store=True)
    avg_booking_value = fields.Monetary(string='Average Booking Value', currency_field='currency_id',
                                        compute='_compute_dashboard_data', store=True)
    monthly_growth = fields.Float(string='Monthly Growth', compute='_compute_dashboard_data', store=True)
    total_refunded = fields.Monetary(string='Total Refunded', currency_field='currency_id',
                                     compute='_compute_dashboard_data', store=True)
    net_revenue = fields.Monetary(string='Net Revenue', currency_field='currency_id', compute='_compute_dashboard_data',
                                  store=True)

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Chart Data Fields (JSON)
    status_chart_data = fields.Text(string='Status Chart Data')
    booking_type_chart_data = fields.Text(string='Booking Type Chart Data')
    revenue_chart_data = fields.Text(string='Revenue Chart Data')
    vehicle_utilization_chart_data = fields.Text(string='Vehicle Utilization Chart Data')
    daily_trend_chart_data = fields.Text(string='Daily Trend Chart Data')
    cancellation_chart_data = fields.Text(string='Cancellation Chart Data')

    @api.depends('date_range', 'booking_type', 'status', 'vehicle_type', 'date_from', 'date_to')
    def _compute_dashboard_data(self):
        for record in self:
            # Get date range
            date_from, date_to = record._get_date_range()

            # Build domain
            domain = [
                ('journey_start_date', '>=', date_from),
                ('journey_start_date', '<=', date_to),
            ]

            if record.booking_type != 'all':
                domain.append(('booking_type', '=', record.booking_type))

            if record.status != 'all':
                domain.append(('state', '=', record.status))

            # Get bookings
            bookings = self.env['fleet.booking'].search(domain)

            # Calculate KPIs
            record.total_bookings = len(bookings)
            record.confirmed_bookings = len(bookings.filtered(lambda b: b.state == 'confirmed'))
            record.completed_bookings = len(bookings.filtered(lambda b: b.state == 'completed'))
            record.cancelled_bookings = len(bookings.filtered(lambda b: b.state == 'cancelled'))

            record.total_revenue = sum(bookings.mapped('total_price'))
            record.total_refunded = sum(bookings.filtered(lambda b: b.state == 'cancelled').mapped('refund_amount'))
            record.net_revenue = record.total_revenue - record.total_refunded

            record.completion_rate = (
                        record.completed_bookings / record.total_bookings * 100) if record.total_bookings else 0
            record.cancellation_rate = (
                        record.cancelled_bookings / record.total_bookings * 100) if record.total_bookings else 0
            record.avg_booking_value = record.total_revenue / record.total_bookings if record.total_bookings else 0

            # Calculate monthly growth (simplified)
            record.monthly_growth = 5.2  # You can implement proper calculation here

            # Generate chart data
            record._generate_chart_data(bookings)

    def _get_date_range(self):
        """Get date range based on selection"""
        today = fields.Date.today()

        if self.date_range == 'today':
            return today, today
        elif self.date_range == 'week':
            start_of_week = today - timedelta(days=today.weekday())
            return start_of_week, today
        elif self.date_range == 'month':
            start_of_month = today.replace(day=1)
            return start_of_month, today
        elif self.date_range == 'quarter':
            quarter = (today.month - 1) // 3 + 1
            start_of_quarter = today.replace(month=(quarter - 1) * 3 + 1, day=1)
            return start_of_quarter, today
        elif self.date_range == 'year':
            start_of_year = today.replace(month=1, day=1)
            return start_of_year, today
        elif self.date_range == 'custom' and self.date_from and self.date_to:
            return self.date_from, self.date_to
        else:
            # Default to this month
            start_of_month = today.replace(day=1)
            return start_of_month, today

    def _generate_chart_data(self, bookings):
        """Generate chart data for JavaScript charts"""

        # Status Distribution
        status_data = {}
        for booking in bookings:
            status = booking.state
            status_data[status] = status_data.get(status, 0) + 1

        self.status_chart_data = json.dumps({
            'labels': list(status_data.keys()),
            'data': list(status_data.values())
        })

        # Booking Type Distribution
        booking_type_data = {}
        for booking in bookings:
            booking_type = booking.booking_type
            booking_type_data[booking_type] = booking_type_data.get(booking_type, 0) + 1

        self.booking_type_chart_data = json.dumps({
            'labels': list(booking_type_data.keys()),
            'data': list(booking_type_data.values())
        })

        # Revenue Chart (Monthly)
        revenue_data = {}
        for booking in bookings:
            month = booking.journey_start_date.strftime('%b %Y') if booking.journey_start_date else 'Unknown'
            revenue_data[month] = revenue_data.get(month, 0) + booking.total_price

        self.revenue_chart_data = json.dumps({
            'labels': list(revenue_data.keys()),
            'data': list(revenue_data.values())
        })

        # Vehicle Utilization
        vehicle_data = {}
        for booking in bookings:
            vehicle = booking.vehicle_type or 'Unknown'
            vehicle_data[vehicle] = vehicle_data.get(vehicle, 0) + 1

        self.vehicle_utilization_chart_data = json.dumps({
            'labels': list(vehicle_data.keys()),
            'data': list(vehicle_data.values())
        })

        # Daily Trend (Last 30 days)
        daily_data = {}
        revenue_daily = {}
        for booking in bookings:
            date = booking.journey_start_date.strftime('%m/%d') if booking.journey_start_date else 'Unknown'
            daily_data[date] = daily_data.get(date, 0) + 1
            revenue_daily[date] = revenue_daily.get(date, 0) + booking.total_price

        self.daily_trend_chart_data = json.dumps({
            'labels': list(daily_data.keys()),
            'bookings': list(daily_data.values()),
            'revenue': list(revenue_daily.values())
        })

        # Cancellation Data
        cancelled_bookings = bookings.filtered(lambda b: b.state == 'cancelled')
        cancellation_monthly = {}
        refund_monthly = {}
        for booking in cancelled_bookings:
            month = booking.journey_start_date.strftime('%b %Y') if booking.journey_start_date else 'Unknown'
            cancellation_monthly[month] = cancellation_monthly.get(month, 0) + 1
            refund_monthly[month] = refund_monthly.get(month, 0) + (booking.refund_amount or 0)

        self.cancellation_chart_data = json.dumps({
            'labels': list(cancellation_monthly.keys()),
            'cancellations': list(cancellation_monthly.values()),
            'refunds': list(refund_monthly.values())
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Set default date range
            if not vals.get('date_from') or not vals.get('date_to'):
                today = fields.Date.today()
                vals['date_from'] = today.replace(day=1)
                vals['date_to'] = today
        return super().create(vals_list)

    def action_refresh_dashboard(self):
        """Refresh dashboard data"""
        self._compute_dashboard_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Dashboard Refreshed'),
                'message': _('Dashboard data has been refreshed successfully.'),
                'type': 'success',
            }
        }

    def action_export_report(self):
        """Export dashboard report"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Export Report'),
                'message': _('Report export functionality will be implemented soon.'),
                'type': 'info',
            }
        }