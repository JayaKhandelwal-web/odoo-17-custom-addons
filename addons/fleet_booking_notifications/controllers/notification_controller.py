# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class FleetNotificationController(http.Controller):
    """
    Controller providing the upcoming journeys data endpoint
    consumed by the frontend notification popup.
    """

    @http.route(
        '/fleet_booking/upcoming_journeys',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False
    )
    def get_upcoming_journeys(self, days=7, **kwargs):
        """
        Returns upcoming fleet bookings for the next N days.
        Excludes cancelled and completed bookings.
        
        :param days: How many days ahead to look (default 7)
        :return: List of journey dicts for the notification popup
        """
        try:
            today = date.today()
            end_date = today + timedelta(days=int(days))

            bookings = request.env['fleet.booking'].search([
                ('journey_start_date', '>=', today.strftime('%Y-%m-%d')),
                ('journey_start_date', '<=', end_date.strftime('%Y-%m-%d')),
                ('state', 'not in', ['cancelled', 'completed']),
            ], order='journey_start_date asc, id asc', limit=50)

            # ── Sort: confirmed first, then by date ──────────────────────
            def sort_key(b):
                state_priority = 0 if b.state == 'confirmed' else 1
                date_val = b.journey_start_date or date.max
                return (state_priority, date_val)

            bookings = sorted(bookings, key=sort_key)

            result = []
            for booking in bookings:
                # Resolve vehicle_type selection label safely
                vehicle_type_label = ''
                if booking.vehicle_type:
                    try:
                        vt_selection = booking._fields['vehicle_type'].selection
                        if callable(vt_selection):
                            vt_selection = vt_selection(booking)
                        vehicle_type_label = dict(vt_selection).get(
                            booking.vehicle_type, booking.vehicle_type
                        )
                    except Exception:
                        vehicle_type_label = booking.vehicle_type or ''

                # Resolve state selection label
                state_label = booking.state or ''
                try:
                    state_selection = booking._fields['state'].selection
                    if callable(state_selection):
                        state_selection = state_selection(booking)
                    state_label = dict(state_selection).get(booking.state, booking.state)
                except Exception:
                    pass

                result.append({
                    'id': booking.id,
                    'name': booking.name or '',
                    'customer_name': (
                        booking.customer_id.name if booking.customer_id else 'N/A'
                    ),
                    # ISO date string for frontend tab filtering
                    'journey_start_date': (
                        booking.journey_start_date.strftime('%Y-%m-%d')
                        if booking.journey_start_date else ''
                    ),
                    # Human-readable date for display
                    'journey_start_date_display': (
                        booking.journey_start_date.strftime('%d %b %Y')
                        if booking.journey_start_date else ''
                    ),
                    'journey_start_time': booking.journey_start_time or '',
                    'journey_start_location': booking.journey_start_location or 'N/A',
                    'journey_end_location': booking.journey_end_location or 'N/A',
                    'vehicle_type': vehicle_type_label,
                    'driver_name': (
                        booking.driver_id.name if booking.driver_id else 'Not Assigned'
                    ),
                    'state': booking.state or '',
                    'state_label': state_label,
                    'total_price': booking.total_price or 0,
                    'passenger_count': booking.passenger_count or 0,
                    'payment_status': booking.payment_status or '',
                    'company_name': booking.company_name or '',
                    'booking_type': booking.booking_type or 'individual',
                })

            _logger.info(
                f"[FleetNotification] Returning {len(result)} upcoming journeys "
                f"for user {request.env.user.name}"
            )
            return result

        except Exception as e:
            _logger.error(
                f"[FleetNotification] Error fetching upcoming journeys: {str(e)}"
            )
            return []
