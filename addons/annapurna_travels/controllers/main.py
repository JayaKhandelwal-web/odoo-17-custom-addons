# -*- coding: utf-8 -*-

import json
from datetime import datetime, timedelta
from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError


class AnnapurnaTravelsController(http.Controller):

    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        """Homepage"""
        # Get services for display
        services = request.env['service.type'].sudo().search([('active', '=', True)])

        # Get featured buses
        buses = request.env['bus.fleet'].sudo().search([
            ('active', '=', True),
            ('state', '=', 'available')
        ], limit=6)

        # Get testimonials
        testimonials = request.env['customer.testimonial'].sudo().search([('active', '=', True)])

        # Get client logos
        client_logos = request.env['annapurna.client.logo'].sudo().search([
            ('active', '=', True)
        ], order='sequence, name')

        # Get tour packages
        tour_packages = request.env['tour.package'].sudo().search([
            ('website_published', '=', True),
            ('state', '=', 'active')
        ], limit=6)

        values = {
            'services': services,
            'buses': buses,
            'testimonials': testimonials,
            'client_logos': client_logos,
            'tour_packages': tour_packages,
        }
        return request.render('annapurna_travels.homepage', values)

    @http.route('/services', type='http', auth="public", website=True)
    def services(self, **kw):
        """Services page"""
        services = request.env['service.type'].sudo().search([('active', '=', True)])
        return request.render('annapurna_travels.services_page', {
            'services': services
        })

    @http.route('/fleet', type='http', auth="public", website=True)
    def fleet(self, category=None, **kw):
        """Fleet page"""
        domain = [('active', '=', True)]

        # Filter by category if specified
        if category:
            domain.append(('category_id.id', '=', int(category)))

        buses = request.env['bus.fleet'].sudo().search(domain)
        categories = request.env['bus.category'].sudo().search([('active', '=', True)])

        return request.render('annapurna_travels.fleet_page', {
            'buses': buses,
            'categories': categories,
            'selected_category': int(category) if category else None
        })

    @http.route('/tours', type='http', auth="public", website=True)
    def tours(self, **kw):
        """Tour packages page"""
        packages = request.env['tour.package'].sudo().search([
            ('website_published', '=', True),
            ('state', '=', 'active')
        ])
        return request.render('annapurna_travels.tours_page', {
            'packages': packages
        })

    @http.route('/tour/<int:package_id>', type='http', auth="public", website=True)
    def tour_detail(self, package_id, **kw):
        """Tour package detail page"""
        package = request.env['tour.package'].sudo().browse(package_id)
        if not package.exists():
            return request.not_found()

        return request.render('annapurna_travels.tour_detail_page', {
            'package': package
        })

    @http.route('/booking', type='http', auth="public", website=True)
    def booking(self, **kw):
        """Booking page"""
        services = request.env['service.type'].sudo().search([('active', '=', True)])
        return request.render('annapurna_travels.booking_page', {
            'services': services,
            'form_data': {}
        })

    @http.route('/booking/submit', type='http', auth="public", website=True, methods=['POST'], csrf=False)
    def booking_submit(self, **post):
        """Handle booking form submission"""
        try:
            # Validate form data
            required_fields = ['customer_name', 'customer_phone', 'service_type_id',
                               'pickup_location', 'pickup_date', 'passenger_count']

            for field in required_fields:
                if not post.get(field):
                    return request.render('annapurna_travels.booking_page', {
                        'error': f'Please fill in the {field.replace("_", " ").title()} field.',
                        'services': request.env['service.type'].sudo().search([('active', '=', True)]),
                        'form_data': post
                    })

            # Create or get customer
            customer_vals = {
                'name': post.get('customer_name'),
                'phone': post.get('customer_phone'),
                'email': post.get('customer_email', ''),
                'street': post.get('customer_address', ''),
                'is_company': False,
                'customer_rank': 1,
            }

            customer = request.env['res.partner'].sudo().search([
                ('phone', '=', post.get('customer_phone'))
            ], limit=1)

            if not customer:
                customer = request.env['res.partner'].sudo().create(customer_vals)

            # Parse pickup date
            pickup_date = datetime.strptime(post.get('pickup_date'), '%Y-%m-%dT%H:%M')
            return_date = None
            if post.get('return_date'):
                return_date = datetime.strptime(post.get('return_date'), '%Y-%m-%dT%H:%M')

            # Get available buses
            available_buses = request.env['bus.booking'].sudo().get_available_buses(pickup_date, return_date)

            if not available_buses:
                return request.render('annapurna_travels.booking_page', {
                    'error': 'No buses available for the selected dates. Please choose different dates.',
                    'services': request.env['service.type'].sudo().search([('active', '=', True)]),
                    'form_data': post
                })

            # Select appropriate bus based on passenger count
            suitable_bus = available_buses.filtered(
                lambda b: b.seating_capacity >= int(post.get('passenger_count'))
            )

            if not suitable_bus:
                return request.render('annapurna_travels.booking_page', {
                    'error': f'No buses available with capacity for {post.get("passenger_count")} passengers.',
                    'services': request.env['service.type'].sudo().search([('active', '=', True)]),
                    'form_data': post
                })

            # Create booking
            booking_vals = {
                'customer_id': customer.id,
                'customer_name': post.get('customer_name'),
                'customer_phone': post.get('customer_phone'),
                'customer_email': post.get('customer_email', ''),
                'customer_address': post.get('customer_address', ''),
                'service_type_id': int(post.get('service_type_id')),
                'bus_id': suitable_bus[0].id,
                'pickup_location': post.get('pickup_location'),
                'drop_location': post.get('drop_location', ''),
                'pickup_date': pickup_date,
                'return_date': return_date,
                'is_round_trip': bool(post.get('is_round_trip')),
                'distance_km': float(post.get('distance_km', 0)),
                'passenger_count': int(post.get('passenger_count')),
                'passenger_details': post.get('passenger_details', ''),
                'special_requirements': post.get('special_requirements', ''),
                'is_website_booking': True,
            }

            booking = request.env['bus.booking'].sudo().create(booking_vals)

            return request.render('annapurna_travels.booking_success', {
                'booking': booking
            })

        except Exception as e:
            return request.render('annapurna_travels.booking_page', {
                'error': f'An error occurred while processing your booking. Please try again or contact us directly.',
                'services': request.env['service.type'].sudo().search([('active', '=', True)]),
                'form_data': post
            })

    @http.route('/booking/check-availability', type='json', auth="public", website=True)
    def check_availability(self, pickup_date, return_date=None, passenger_count=1):
        """AJAX endpoint to check bus availability"""
        try:
            pickup_dt = datetime.strptime(pickup_date, '%Y-%m-%dT%H:%M')
            return_dt = None
            if return_date:
                return_dt = datetime.strptime(return_date, '%Y-%m-%dT%H:%M')

            available_buses = request.env['bus.booking'].sudo().get_available_buses(pickup_dt, return_dt)
            suitable_buses = available_buses.filtered(
                lambda b: b.seating_capacity >= int(passenger_count)
            )

            return {
                'available': len(suitable_buses) > 0,
                'buses': [{
                    'id': bus.id,
                    'name': bus.name,
                    'category': bus.category_id.name,
                    'capacity': bus.seating_capacity,
                    'daily_rate': bus.daily_rate,
                } for bus in suitable_buses[:5]]
            }
        except:
            return {'available': False, 'buses': []}

    @http.route('/about', type='http', auth="public", website=True)
    def about(self, **kw):
        """About us page"""
        return request.render('annapurna_travels.about_page')

    @http.route('/contact', type='http', auth="public", website=True)
    def contact(self, **kw):
        """Contact page"""
        return request.render('annapurna_travels.contact_page')

    @http.route('/contact/submit', type='http', auth="public", website=True, methods=['POST'], csrf=False)
    def contact_submit(self, **post):
        """Handle contact form submission"""
        try:
            # Create lead/inquiry
            vals = {
                'name': post.get('subject', 'Website Inquiry'),
                'contact_name': post.get('name'),
                'email_from': post.get('email'),
                'phone': post.get('phone'),
                'description': post.get('message'),
            }

            # If CRM is installed, create lead
            if 'crm.lead' in request.env:
                request.env['crm.lead'].sudo().create(vals)

            return request.render('annapurna_travels.contact_success')

        except:
            return request.render('annapurna_travels.contact_page', {
                'error': 'An error occurred while sending your message. Please try again.',
                'form_data': post
            })

    @http.route('/gallery', type='http', auth="public", website=True)
    def gallery(self, **kw):
        """Gallery page"""
        buses = request.env['bus.fleet'].sudo().search([('active', '=', True)])
        packages = request.env['tour.package'].sudo().search([('website_published', '=', True)])

        return request.render('annapurna_travels.gallery_page', {
            'buses': buses,
            'packages': packages
        })

    @http.route('/bus/<int:bus_id>', type='http', auth="public", website=True)
    def bus_detail(self, bus_id, **kw):
        """Bus detail page with full specifications"""
        bus = request.env['bus.fleet'].sudo().browse(bus_id)
        if not bus.exists() or not bus.active:
            return request.not_found()

        # Get related buses from same category
        related_buses = request.env['bus.fleet'].sudo().search([
            ('category_id', '=', bus.category_id.id),
            ('id', '!=', bus.id),
            ('active', '=', True)
        ], limit=4)

        # Get all images including main image and additional images
        all_images = []
        if bus.image:
            all_images.append({
                'image': bus.image,
                'name': f"{bus.name} - Main View",
                'is_main': True
            })

        for img in bus.images:
            all_images.append({
                'image': img.image,
                'name': img.name or f"{bus.name} - Additional View",
                'is_main': False
            })

        values = {
            'bus': bus,
            'related_buses': related_buses,
            'all_images': all_images,
            'youtube_video_id': bus.get_youtube_video_id(),
            'youtube_thumbnail': bus.get_youtube_thumbnail_url(),
            'youtube_embed_url': bus.get_youtube_embed_url(),
            'video_url': bus.get_video_url(),
            'has_mp4_video': bool(bus.video_file),
            'has_youtube_video': bool(bus.youtube_video_url),
        }

        return request.render('annapurna_travels.bus_detail_page', values)

    @http.route('/bus/<int:bus_id>/video', type='json', auth="public", website=True)
    def get_bus_video_details(self, bus_id):
        """AJAX endpoint to get video details"""
        bus = request.env['bus.fleet'].sudo().browse(bus_id)
        if not bus.exists():
            return {'error': 'Bus not found'}

        return {
            'video_id': bus.get_youtube_video_id(),
            'embed_url': bus.get_youtube_embed_url(),
            'thumbnail_url': bus.get_youtube_thumbnail_url(),
            'has_youtube_video': bool(bus.youtube_video_url),
            'video_url': bus.get_video_url(),
            'has_mp4_video': bool(bus.video_file),
            'has_video': bus.has_video
        }

    @http.route('/my/bookings', type='http', auth="user", website=True)
    def my_bookings(self, **kw):
        """User's bookings page - requires login"""
        user = request.env.user

        # Get user's bookings
        bookings = request.env['bus.booking'].sudo().search([
            ('customer_id', '=', user.partner_id.id)
        ], order='pickup_date desc')

        # Get user's tour bookings if tour booking model exists
        tour_bookings = []
        if 'tour.booking' in request.env:
            tour_bookings = request.env['tour.booking'].sudo().search([
                ('customer_id', '=', user.partner_id.id)
            ], order='create_date desc')

        return request.render('annapurna_travels.my_bookings_page', {
            'bookings': bookings,
            'tour_bookings': tour_bookings,
            'user': user
        })

    @http.route(['/clients'], type='http', auth="public", website=True)
    def clients_page(self, **kwargs):
        """Clients page"""
        client_logos = request.env['annapurna.client.logo'].sudo().search([
            ('active', '=', True)
        ], order='sequence, name')

        return request.render('annapurna_travels.clients_page', {
            'client_logos': client_logos,
        })