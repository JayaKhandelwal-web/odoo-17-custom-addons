# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError
import json
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class FleetBookingController(http.Controller):
    """
    Combined controller for both dashboard functionality and public invoice URLs
    """

    # =========================
    # DASHBOARD ROUTES
    # =========================

    @http.route('/fleet_booking/dashboard', auth='user', website=True)
    def dashboard(self, **kwargs):
        """Main dashboard route"""
        try:
            dashboard_data = self._get_dashboard_data()

            # Ensure all required data is present with defaults
            dashboard_data.setdefault('total_bookings', 0)
            dashboard_data.setdefault('confirmed_bookings', 0)
            dashboard_data.setdefault('completed_bookings', 0)
            dashboard_data.setdefault('cancelled_bookings', 0)
            dashboard_data.setdefault('total_revenue', 0)
            dashboard_data.setdefault('completion_rate', 0)

            # Ensure chart data has proper structure
            dashboard_data.setdefault('statusDistribution', {'labels': [], 'data': []})
            dashboard_data.setdefault('bookingTypes', {'labels': [], 'data': []})
            dashboard_data.setdefault('monthlyRevenue', {'labels': [], 'data': []})
            dashboard_data.setdefault('vehicleUtilization', {'labels': [], 'data': []})
            dashboard_data.setdefault('dailyTrend', {'labels': [], 'bookings': [], 'revenue': []})
            dashboard_data.setdefault('cancellationData', {'labels': [], 'cancellations': [], 'refunds': []})

            dashboard_data_json = json.dumps(dashboard_data, default=str, ensure_ascii=False)

            return request.render('fleet_booking.fleet_booking_dashboard_template', {
                'dashboard_data': dashboard_data,
                'dashboard_data_json': dashboard_data_json
            })
        except Exception as e:
            # Log the error and return with empty data
            _logger.error(f"Dashboard error: {str(e)}")

            empty_data = {
                'total_bookings': 0,
                'confirmed_bookings': 0,
                'completed_bookings': 0,
                'cancelled_bookings': 0,
                'total_revenue': 0,
                'completion_rate': 0,
                'statusDistribution': {'labels': [], 'data': []},
                'bookingTypes': {'labels': [], 'data': []},
                'monthlyRevenue': {'labels': [], 'data': []},
                'vehicleUtilization': {'labels': [], 'data': []},
                'dailyTrend': {'labels': [], 'bookings': [], 'revenue': []},
                'cancellationData': {'labels': [], 'cancellations': [], 'refunds': []}
            }

            return request.render('fleet_booking.fleet_booking_dashboard_template', {
                'dashboard_data': empty_data,
                'dashboard_data_json': json.dumps(empty_data)
            })

    @http.route('/fleet_booking/dashboard_data', type='json', auth='user', methods=['POST'], csrf=False)
    def dashboard_data(self, **filters):
        """API endpoint for filtered dashboard data"""
        try:
            return self._get_dashboard_data(filters)
        except Exception as e:
            _logger.error(f"Dashboard data error: {str(e)}")
            return {
                'error': str(e),
                'total_bookings': 0,
                'confirmed_bookings': 0,
                'completed_bookings': 0,
                'cancelled_bookings': 0,
                'total_revenue': 0,
                'completion_rate': 0,
                'statusDistribution': {'labels': [], 'data': []},
                'bookingTypes': {'labels': [], 'data': []},
                'monthlyRevenue': {'labels': [], 'data': []},
                'vehicleUtilization': {'labels': [], 'data': []},
                'dailyTrend': {'labels': [], 'bookings': [], 'revenue': []},
                'cancellationData': {'labels': [], 'cancellations': [], 'refunds': []}
            }

    @http.route('/fleet_booking/dashboard/export', auth='user', methods=['GET'])
    def export_dashboard_data(self, **kwargs):
        """Export dashboard data as CSV"""
        try:
            dashboard_data = self._get_dashboard_data()

            # Create CSV content
            csv_content = "Fleet Booking Dashboard Export\n"
            csv_content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            # Basic stats
            csv_content += "Basic Statistics:\n"
            csv_content += f"Total Bookings,{dashboard_data['total_bookings']}\n"
            csv_content += f"Confirmed Bookings,{dashboard_data['confirmed_bookings']}\n"
            csv_content += f"Completed Bookings,{dashboard_data['completed_bookings']}\n"
            csv_content += f"Cancelled Bookings,{dashboard_data['cancelled_bookings']}\n"
            csv_content += f"Total Revenue,{dashboard_data['total_revenue']}\n"
            csv_content += f"Completion Rate,{dashboard_data['completion_rate']}%\n\n"

            # Status distribution
            csv_content += "Status Distribution:\n"
            for i, label in enumerate(dashboard_data['statusDistribution']['labels']):
                csv_content += f"{label},{dashboard_data['statusDistribution']['data'][i]}\n"

            # Set headers for CSV download
            headers = [
                ('Content-Type', 'text/csv'),
                ('Content-Disposition',
                 f'attachment; filename="fleet_dashboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"')
            ]

            return request.make_response(csv_content, headers=headers)
        except Exception as e:
            return request.make_response(f"Error generating CSV: {str(e)}", status=500)

    # =========================
    # PUBLIC INVOICE ROUTES
    # =========================

    @http.route(['/fleet/booking/<int:booking_id>/invoice/<string:access_token>'],
                type='http', auth="public", website=True, csrf=False)
    def fleet_booking_invoice_public(self, booking_id, access_token, **kwargs):
        """
        Public route to view fleet booking invoice using access token
        This allows anyone with the URL to view the invoice without authentication
        """
        try:
            # Find the booking by ID and access token
            booking = request.env['fleet.booking'].sudo().search([
                ('id', '=', booking_id),
                ('invoice_access_token', '=', access_token)
            ], limit=1)

            if not booking:
                return request.render('fleet_booking.invoice_access_error', {
                    'error_title': _('Invalid Invoice Link'),
                    'error_message': _(
                        'The invoice link is invalid or has expired. Please contact the company for a new link.'),
                    'booking_id': booking_id
                })

            # Check if booking exists and token is valid
            if not booking.invoice_access_token or booking.invoice_access_token != access_token:
                return request.render('fleet_booking.invoice_access_error', {
                    'error_title': _('Access Denied'),
                    'error_message': _('You do not have permission to view this invoice.'),
                    'booking_id': booking_id
                })

            # Log access for security purposes
            _logger.info(f"Public invoice access for booking {booking.name} from IP: {request.httprequest.remote_addr}")

            # Render the invoice template with booking data
            return request.render('fleet_booking.public_invoice_template', {
                'booking': booking,
                'company': booking.company_id,
                'access_token': access_token,
                'show_public_header': True
            })

        except Exception as e:
            _logger.error(f"Error accessing public invoice for booking {booking_id}: {str(e)}")
            return request.render('fleet_booking.invoice_access_error', {
                'error_title': _('Server Error'),
                'error_message': _('An error occurred while loading the invoice. Please try again later.'),
                'booking_id': booking_id
            })

    @http.route(['/fleet/booking/<int:booking_id>/invoice/<string:access_token>/pdf'],
                type='http', auth="public", website=True, csrf=False)
    def fleet_booking_invoice_pdf_public(self, booking_id, access_token, **kwargs):
        """
        Public route to download fleet booking invoice as PDF
        """
        try:
            # Find the booking by ID and access token
            booking = request.env['fleet.booking'].sudo().search([
                ('id', '=', booking_id),
                ('invoice_access_token', '=', access_token)
            ], limit=1)

            if not booking or not booking.invoice_access_token or booking.invoice_access_token != access_token:
                return request.render('fleet_booking.invoice_access_error', {
                    'error_title': _('Access Denied'),
                    'error_message': _('You do not have permission to download this invoice.'),
                    'booking_id': booking_id
                })

            # Log PDF download
            _logger.info(
                f"Public invoice PDF download for booking {booking.name} from IP: {request.httprequest.remote_addr}")

            # Generate and return PDF
            report = request.env.ref('fleet_booking.action_report_fleet_booking_invoice').sudo()
            pdf_content, _ = report._render_qweb_pdf([booking.id])

            pdf_http_headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf_content)),
                ('Content-Disposition', f'inline; filename="Invoice-{booking.name}.pdf"'),
            ]

            return request.make_response(pdf_content, headers=pdf_http_headers)

        except Exception as e:
            _logger.error(f"Error downloading public invoice PDF for booking {booking_id}: {str(e)}")
            return request.render('fleet_booking.invoice_access_error', {
                'error_title': _('Server Error'),
                'error_message': _('An error occurred while generating the PDF. Please try again later.'),
                'booking_id': booking_id
            })

    @http.route(['/fleet/booking/<int:booking_id>/invoice/<string:access_token>/print'],
                type='http', auth="public", website=True, csrf=False)
    def fleet_booking_invoice_print_public(self, booking_id, access_token, **kwargs):
        """
        Public route to view fleet booking invoice in print-friendly format
        """
        try:
            # Find the booking by ID and access token
            booking = request.env['fleet.booking'].sudo().search([
                ('id', '=', booking_id),
                ('invoice_access_token', '=', access_token)
            ], limit=1)

            if not booking or not booking.invoice_access_token or booking.invoice_access_token != access_token:
                return request.render('fleet_booking.invoice_access_error', {
                    'error_title': _('Access Denied'),
                    'error_message': _('You do not have permission to view this invoice.'),
                    'booking_id': booking_id
                })

            # Log print access
            _logger.info(
                f"Public invoice print view for booking {booking.name} from IP: {request.httprequest.remote_addr}")

            # Render the print-friendly invoice template
            return request.render('fleet_booking.public_invoice_print_template', {
                'booking': booking,
                'company': booking.company_id,
                'access_token': access_token,
                'print_mode': True
            })

        except Exception as e:
            _logger.error(f"Error accessing print invoice for booking {booking_id}: {str(e)}")
            return request.render('fleet_booking.invoice_access_error', {
                'error_title': _('Server Error'),
                'error_message': _('An error occurred while loading the print view. Please try again later.'),
                'booking_id': booking_id
            })

    @http.route(['/fleet/booking/invoice/validate'],
                type='json', auth="public", methods=['POST'], csrf=False)
    def validate_invoice_access(self, booking_id, access_token, **kwargs):
        """
        JSON endpoint to validate invoice access token
        Useful for AJAX validation before showing invoice links
        """
        try:
            booking = request.env['fleet.booking'].sudo().search([
                ('id', '=', booking_id),
                ('invoice_access_token', '=', access_token)
            ], limit=1)

            if booking and booking.invoice_access_token == access_token:
                return {
                    'success': True,
                    'booking_name': booking.name,
                    'customer_name': booking.customer_id.name,
                    'total_amount': booking.total_price,
                    'currency': booking.currency_id.name
                }
            else:
                return {
                    'success': False,
                    'error': 'Invalid access token'
                }

        except Exception as e:
            _logger.error(f"Error validating invoice access: {str(e)}")
            return {
                'success': False,
                'error': 'Server error occurred'
            }

    @http.route(['/fleet/booking/invoice/generate-token'],
                type='json', auth="user", methods=['POST'], csrf=False)
    def generate_invoice_token(self, booking_id, **kwargs):
        """
        Authenticated endpoint to generate/regenerate invoice access token
        Only accessible by logged-in users with appropriate permissions
        """
        try:
            # Check if user has permission to access the booking
            booking = request.env['fleet.booking'].browse(booking_id)

            if not booking.exists():
                return {'success': False, 'error': 'Booking not found'}

            # Generate new token
            token = booking._get_or_create_invoice_access_token()

            return {
                'success': True,
                'access_token': token,
                'invoice_url': booking.invoice_url,
                'booking_name': booking.name
            }

        except AccessError:
            return {'success': False, 'error': 'Access denied'}
        except Exception as e:
            _logger.error(f"Error generating invoice token: {str(e)}")
            return {'success': False, 'error': 'Server error occurred'}

    @http.route(['/fleet/booking/invoice/revoke-token'],
                type='json', auth="user", methods=['POST'], csrf=False)
    def revoke_invoice_token(self, booking_id, **kwargs):
        """
        Authenticated endpoint to revoke invoice access token
        This will make the current shareable URL invalid
        """
        try:
            # Check if user has permission to access the booking
            booking = request.env['fleet.booking'].browse(booking_id)

            if not booking.exists():
                return {'success': False, 'error': 'Booking not found'}

            # Revoke token by setting it to False
            booking.sudo().write({'invoice_access_token': False})

            return {
                'success': True,
                'message': 'Invoice access token has been revoked',
                'booking_name': booking.name
            }

        except AccessError:
            return {'success': False, 'error': 'Access denied'}
        except Exception as e:
            _logger.error(f"Error revoking invoice token: {str(e)}")
            return {'success': False, 'error': 'Server error occurred'}

    # =========================
    # DASHBOARD HELPER METHODS
    # =========================

    def _get_dashboard_data(self, filters=None):
        """Get comprehensive dashboard data with optional filters"""

        if not filters:
            filters = {}

        # Check if fleet.booking model exists
        try:
            booking_model = request.env['fleet.booking']
        except KeyError:
            # If model doesn't exist, return empty data
            return self._get_empty_dashboard_data()

        # Get domain based on filters
        domain = self._build_domain(filters)

        # Basic statistics
        stats = self._get_basic_stats(booking_model, domain)

        # Chart data
        charts_data = self._get_charts_data(booking_model, domain, filters)

        # Combine all data
        dashboard_data = {
            **stats,
            **charts_data
        }

        return dashboard_data

    def _get_empty_dashboard_data(self):
        """Return empty dashboard data structure"""
        return {
            'total_bookings': 0,
            'confirmed_bookings': 0,
            'completed_bookings': 0,
            'cancelled_bookings': 0,
            'total_revenue': 0,
            'completion_rate': 0,
            'statusDistribution': {'labels': ['No Data'], 'data': [1]},
            'bookingTypes': {'labels': ['No Data'], 'data': [1]},
            'monthlyRevenue': {'labels': ['Jan', 'Feb', 'Mar', 'Apr'], 'data': [0, 0, 0, 0]},
            'vehicleUtilization': {'labels': ['No Vehicles'], 'data': [0]},
            'dailyTrend': {'labels': ['Day 1', 'Day 2'], 'bookings': [0, 0], 'revenue': [0, 0]},
            'cancellationData': {'labels': ['Jan', 'Feb'], 'cancellations': [0, 0], 'refunds': [0, 0]}
        }

    def _build_domain(self, filters):
        """Build domain based on filters"""
        domain = []

        # Date range filter
        if filters.get('fromDate') and filters.get('toDate'):
            domain.extend([
                ('journey_start_date', '>=', filters['fromDate']),
                ('journey_start_date', '<=', filters['toDate'])
            ])
        elif filters.get('dateRange'):
            date_range = filters['dateRange']
            today = datetime.now().date()

            if date_range == 'today':
                domain.append(('journey_start_date', '=', today))
            elif date_range == 'week':
                week_start = today - timedelta(days=today.weekday())
                domain.extend([
                    ('journey_start_date', '>=', week_start),
                    ('journey_start_date', '<=', today)
                ])
            elif date_range == 'month':
                month_start = today.replace(day=1)
                domain.extend([
                    ('journey_start_date', '>=', month_start),
                    ('journey_start_date', '<=', today)
                ])
            elif date_range == 'quarter':
                quarter_start = datetime(today.year, ((today.month - 1) // 3) * 3 + 1, 1).date()
                domain.extend([
                    ('journey_start_date', '>=', quarter_start),
                    ('journey_start_date', '<=', today)
                ])
            elif date_range == 'year':
                year_start = today.replace(month=1, day=1)
                domain.extend([
                    ('journey_start_date', '>=', year_start),
                    ('journey_start_date', '<=', today)
                ])

        # Booking type filter
        if filters.get('bookingType') and filters['bookingType'] != 'all':
            domain.append(('booking_type', '=', filters['bookingType']))

        # Status filter
        if filters.get('status') and filters['status'] != 'all':
            domain.append(('state', '=', filters['status']))

        # Vehicle type filter
        if filters.get('vehicleType') and filters['vehicleType'] != 'all':
            vehicle_type = filters['vehicleType']
            if vehicle_type == 'luxury':
                domain.append(('vehicle_type', 'in', [
                    '17_Seater_Luxury_force_Traveller',
                    '26_Seater_Luxury_Force_Traveller',
                    '33_Seater_Super_Luxury_Recliner_AC_Coach',
                    '41_Seater_Super_Luxury_Recliner_AC_Coach'
                ]))
            elif vehicle_type == 'coach':
                domain.append(('vehicle_type', 'in', [
                    '48_Seater_Luxury_AC_Coach',
                    '49_Seater_Super_Luxury_AC_Coach_2024',
                    '50_Seater_Super_Luxury_AC_Coach_2025'
                ]))
            elif vehicle_type == 'sedan':
                domain.append(('vehicle_type', 'in', [
                    'Toyota_Innova',
                    'Toyota_Innova_Crysta',
                    'Ertiga',
                    'Honda_Amaze',
                    'Hyundai_Aura',
                    'Hyundai_Xcent'
                ]))

        return domain

    def _get_basic_stats(self, booking_model, domain):
        """Get basic statistics"""
        try:
            # Total bookings
            total_bookings = booking_model.search_count(domain)

            # Status-wise counts
            confirmed_bookings = booking_model.search_count(domain + [('state', '=', 'confirmed')])
            completed_bookings = booking_model.search_count(domain + [('state', '=', 'completed')])
            cancelled_bookings = booking_model.search_count(domain + [('state', '=', 'cancelled')])

            # Revenue calculation
            completed_domain = domain + [('state', '=', 'completed')]
            completed_records = booking_model.search(completed_domain)
            total_revenue = sum(record.total_price for record in completed_records if
                                hasattr(record, 'total_price') and record.total_price)

            # Completion rate
            completion_rate = 0
            if total_bookings > 0:
                completion_rate = round((completed_bookings / total_bookings) * 100, 1)

            return {
                'total_bookings': total_bookings,
                'confirmed_bookings': confirmed_bookings,
                'completed_bookings': completed_bookings,
                'cancelled_bookings': cancelled_bookings,
                'total_revenue': total_revenue,
                'completion_rate': completion_rate
            }
        except Exception as e:
            _logger.error(f"Error getting basic stats: {str(e)}")
            return {
                'total_bookings': 0,
                'confirmed_bookings': 0,
                'completed_bookings': 0,
                'cancelled_bookings': 0,
                'total_revenue': 0,
                'completion_rate': 0
            }

    def _get_charts_data(self, booking_model, domain, filters):
        """Get data for all charts"""
        try:
            # Status Distribution
            status_data = self._get_status_distribution(booking_model, domain)

            # Booking Types Distribution
            booking_type_data = self._get_booking_type_distribution(booking_model, domain)

            # Monthly Revenue
            monthly_revenue_data = self._get_monthly_revenue(booking_model, domain)

            # Vehicle Utilization
            vehicle_utilization_data = self._get_vehicle_utilization(booking_model, domain)

            # Daily Trend
            daily_trend_data = self._get_daily_trend(booking_model, domain)

            # Cancellation Analysis
            cancellation_data = self._get_cancellation_analysis(booking_model, domain)

            return {
                'statusDistribution': status_data,
                'bookingTypes': booking_type_data,
                'monthlyRevenue': monthly_revenue_data,
                'vehicleUtilization': vehicle_utilization_data,
                'dailyTrend': daily_trend_data,
                'cancellationData': cancellation_data
            }
        except Exception as e:
            _logger.error(f"Error getting charts data: {str(e)}")
            return {
                'statusDistribution': {'labels': [], 'data': []},
                'bookingTypes': {'labels': [], 'data': []},
                'monthlyRevenue': {'labels': [], 'data': []},
                'vehicleUtilization': {'labels': [], 'data': []},
                'dailyTrend': {'labels': [], 'bookings': [], 'revenue': []},
                'cancellationData': {'labels': [], 'cancellations': [], 'refunds': []}
            }

    def _get_status_distribution(self, booking_model, domain):
        """Get booking status distribution for pie chart"""
        try:
            statuses = ['enquiry', 'quotation', 'followup', 'confirmed', 'completed', 'cancelled']
            status_labels = ['Enquiry', 'Quotation', 'Follow Up', 'Confirmed', 'Completed', 'Cancelled']

            data = []
            for status in statuses:
                count = booking_model.search_count(domain + [('state', '=', status)])
                data.append(count)

            # Filter out zero values for better visualization
            filtered_labels = []
            filtered_data = []
            for i, count in enumerate(data):
                if count > 0:
                    filtered_labels.append(status_labels[i])
                    filtered_data.append(count)

            # If no data, show at least one item
            if not filtered_data:
                filtered_labels = ['No Data']
                filtered_data = [1]

            return {
                'labels': filtered_labels,
                'data': filtered_data
            }
        except Exception as e:
            return {'labels': ['No Data'], 'data': [1]}

    def _get_booking_type_distribution(self, booking_model, domain):
        """Get booking type distribution for doughnut chart"""
        try:
            individual_count = booking_model.search_count(domain + [('booking_type', '=', 'individual')])
            company_count = booking_model.search_count(domain + [('booking_type', '=', 'company')])

            if individual_count == 0 and company_count == 0:
                return {'labels': ['No Data'], 'data': [1]}

            return {
                'labels': ['Individual', 'Company'],
                'data': [individual_count, company_count]
            }
        except Exception as e:
            return {'labels': ['No Data'], 'data': [1]}

    def _get_monthly_revenue(self, booking_model, domain):
        """Get monthly revenue data for column chart"""
        try:
            # Get current year data
            current_year = datetime.now().year
            months = []
            revenue_data = []

            for month in range(1, 13):
                month_start = datetime(current_year, month, 1).date()
                if month == 12:
                    month_end = datetime(current_year + 1, 1, 1).date() - timedelta(days=1)
                else:
                    month_end = datetime(current_year, month + 1, 1).date() - timedelta(days=1)

                month_domain = domain + [
                    ('journey_start_date', '>=', month_start),
                    ('journey_start_date', '<=', month_end),
                    ('state', '=', 'completed')
                ]

                records = booking_model.search(month_domain)
                month_revenue = sum(
                    record.total_price for record in records if hasattr(record, 'total_price') and record.total_price)

                months.append(month_start.strftime('%b'))
                revenue_data.append(month_revenue)

            return {
                'labels': months,
                'data': revenue_data
            }
        except Exception as e:
            return {
                'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                'data': [0] * 12
            }

    def _get_vehicle_utilization(self, booking_model, domain):
        """Get vehicle utilization data"""
        try:
            vehicle_types = [
                ('17_Seater_Luxury_force_Traveller', '17 Seater Traveller'),
                ('26_Seater_Luxury_Force_Traveller', '26 Seater Traveller'),
                ('33_Seater_Super_Luxury_Recliner_AC_Coach', '33 Seater Coach'),
                ('41_Seater_Super_Luxury_Recliner_AC_Coach', '41 Seater Coach'),
                ('48_Seater_Luxury_AC_Coach', '48 Seater Coach'),
                ('Toyota_Innova', 'Toyota Innova'),
                ('Ertiga', 'Ertiga'),
                ('Honda_Amaze', 'Honda Amaze')
            ]

            labels = []
            utilization_data = []

            total_bookings = booking_model.search_count(domain)

            for vehicle_type, label in vehicle_types:
                vehicle_bookings = booking_model.search_count(
                    domain + [('vehicle_type', '=', vehicle_type)]
                )

                # Calculate utilization percentage
                utilization = 0
                if total_bookings > 0:
                    utilization = round((vehicle_bookings / total_bookings) * 100, 1)

                if utilization > 0:  # Only include vehicles with bookings
                    labels.append(label)
                    utilization_data.append(utilization)

            if not labels:
                labels = ['No Vehicles']
                utilization_data = [0]

            return {
                'labels': labels,
                'data': utilization_data
            }
        except Exception as e:
            return {'labels': ['No Data'], 'data': [0]}

    def _get_daily_trend(self, booking_model, domain):
        """Get daily trend data for line chart (last 30 days)"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=29)

            labels = []
            bookings_data = []
            revenue_data = []

            current_date = start_date
            while current_date <= end_date:
                day_domain = domain + [('journey_start_date', '=', current_date)]

                # Count bookings for the day
                day_bookings = booking_model.search_count(day_domain)

                # Calculate revenue for completed bookings on this day
                day_revenue_domain = day_domain + [('state', '=', 'completed')]
                day_records = booking_model.search(day_revenue_domain)
                day_revenue = sum(record.total_price for record in day_records if
                                  hasattr(record, 'total_price') and record.total_price)

                labels.append(current_date.strftime('%b %d'))
                bookings_data.append(day_bookings)
                revenue_data.append(day_revenue)

                current_date += timedelta(days=1)

            return {
                'labels': labels,
                'bookings': bookings_data,
                'revenue': revenue_data
            }
        except Exception as e:
            return {
                'labels': ['Day 1', 'Day 2'],
                'bookings': [0, 0],
                'revenue': [0, 0]
            }

    def _get_cancellation_analysis(self, booking_model, domain):
        """Get cancellation and refund analysis data"""
        try:
            current_year = datetime.now().year
            months = []
            cancellation_data = []
            refund_data = []

            for month in range(1, 13):
                month_start = datetime(current_year, month, 1).date()
                if month == 12:
                    month_end = datetime(current_year + 1, 1, 1).date() - timedelta(days=1)
                else:
                    month_end = datetime(current_year, month + 1, 1).date() - timedelta(days=1)

                # Cancellations in this month
                cancel_domain = domain + [
                    ('journey_start_date', '>=', month_start),
                    ('journey_start_date', '<=', month_end),
                    ('state', '=', 'cancelled')
                ]

                month_cancellations = booking_model.search_count(cancel_domain)

                # Refunds in this month
                try:
                    refund_records = booking_model.search(cancel_domain)
                    month_refunds = sum(record.refund_amount for record in refund_records if
                                        hasattr(record, 'refund_amount') and record.refund_amount)
                except:
                    month_refunds = 0

                months.append(month_start.strftime('%b'))
                cancellation_data.append(month_cancellations)
                refund_data.append(month_refunds)

            return {
                'labels': months,
                'cancellations': cancellation_data,
                'refunds': refund_data
            }
        except Exception as e:
            return {
                'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                'cancellations': [0] * 12,
                'refunds': [0] * 12
            }