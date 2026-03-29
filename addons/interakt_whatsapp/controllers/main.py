from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class FleetBookingQuotationController(http.Controller):
    
    @http.route(['/fleet/booking/<int:booking_id>/quotation/<string:access_token>'], 
                type='http', auth='public', website=True)
    def fleet_booking_quotation_pdf(self, booking_id, access_token, **kwargs):
        """Public route to access quotation PDF"""
        try:
            booking = request.env['fleet.booking'].sudo().browse(booking_id)
            
            # Validate booking exists and token matches
            if not booking.exists():
                return request.render('website.404')
            
            if booking.invoice_access_token != access_token:
                return request.render('website.403')
            
            # Generate PDF report (you can use the same invoice report or create a separate quotation report)
            # Using the same invoice report for now
            pdf, _ = request.env.ref('fleet_booking.action_report_fleet_booking_invoice').sudo()._render_qweb_pdf([booking_id])
            
            pdfhttpheaders = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf)),
                ('Content-Disposition', f'inline; filename="Quotation_{booking.name}.pdf"'),
            ]
            
            return request.make_response(pdf, headers=pdfhttpheaders)
            
        except Exception as e:
            _logger.error(f"Error generating quotation PDF: {str(e)}")
            return request.render('website.404')
