# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CustomerTestimonial(models.Model):
    _name = 'customer.testimonial'
    _description = 'Customer Testimonial'
    _order = 'sequence, create_date desc'
    _rec_name = 'name'

    name = fields.Char('Customer Name', required=True)
    customer_id = fields.Many2one('res.partner', 'Customer')
    designation = fields.Char('Designation/Location')
    company = fields.Char('Company')

    # Testimonial Content
    testimonial = fields.Text('Testimonial', required=True)
    testimonial_excerpt = fields.Char(
        'Testimonial Excerpt',
        compute='_compute_testimonial_excerpt',
        store=True,
        help="Automatically generated excerpt of the testimonial"
    )
    rating = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars')
    ], string='Rating', default='5', required=True)

    # Display Settings
    sequence = fields.Integer('Sequence', default=10)
    image = fields.Binary('Customer Photo')

    # Related Booking
    booking_id = fields.Many2one('bus.booking', 'Related Booking')
    tour_booking_id = fields.Many2one('tour.booking', 'Related Tour Booking')
    service_type_id = fields.Many2one('service.type', 'Service Used')

    # Publication
    website_published = fields.Boolean('Published on Website', default=True)
    approved = fields.Boolean('Approved', default=False)
    approved_by = fields.Many2one('res.users', 'Approved By', readonly=True)
    approved_date = fields.Datetime('Approved Date', readonly=True)

    # Dates
    testimonial_date = fields.Date('Testimonial Date', default=fields.Date.today, required=True)

    active = fields.Boolean('Active', default=True)

    @api.depends('testimonial')
    def _compute_testimonial_excerpt(self):
        """Compute testimonial excerpt for display purposes"""
        for record in self:
            if record.testimonial:
                # Clean the text and create excerpt
                clean_text = record.testimonial.strip()
                if len(clean_text) > 100:
                    # Find the last space before 100 characters to avoid cutting words
                    excerpt = clean_text[:100]
                    last_space = excerpt.rfind(' ')
                    if last_space > 80:  # Only if we can get at least 80 characters
                        excerpt = excerpt[:last_space]
                    record.testimonial_excerpt = excerpt + '...'
                else:
                    record.testimonial_excerpt = clean_text
            else:
                record.testimonial_excerpt = ''

    def action_approve(self):
        """Approve testimonial"""
        for record in self:
            record.write({
                'approved': True,
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now()
            })
        return True

    def action_reject(self):
        """Reject testimonial and unpublish from website"""
        for record in self:
            record.write({
                'approved': False,
                'website_published': False,
                'approved_by': False,
                'approved_date': False
            })
        return True

    def action_toggle_website_published(self):
        """Toggle website published status"""
        for record in self:
            record.website_published = not record.website_published
        return True

    @api.model
    def get_website_testimonials(self, limit=None):
        """Get approved testimonials for website display"""
        domain = [
            ('website_published', '=', True),
            ('approved', '=', True),
            ('active', '=', True)
        ]
        return self.search(domain, order='sequence, create_date desc', limit=limit)

    @api.model
    def get_testimonials_by_rating(self, rating, limit=None):
        """Get testimonials filtered by rating"""
        domain = [
            ('website_published', '=', True),
            ('approved', '=', True),
            ('active', '=', True),
            ('rating', '=', str(rating))
        ]
        return self.search(domain, order='sequence, create_date desc', limit=limit)

    def name_get(self):
        """Custom name_get to show customer name with rating"""
        result = []
        for record in self:
            stars = '⭐' * int(record.rating) if record.rating else ''
            name = f"{record.name} ({stars})"
            result.append((record.id, name))
        return result

    @api.model
    def create(self, vals):
        """Override create to set sequence if not provided"""
        if 'sequence' not in vals or vals['sequence'] == 0:
            # Get the highest sequence number and add 10
            max_sequence = self.search([], order='sequence desc', limit=1).sequence or 0
            vals['sequence'] = max_sequence + 10
        return super().create(vals)

    def write(self, vals):
        """Override write to handle approval logic"""
        # If approving, ensure approved_by and approved_date are set
        if vals.get('approved') and not vals.get('approved_by'):
            vals['approved_by'] = self.env.user.id
            vals['approved_date'] = fields.Datetime.now()

        # If rejecting, clear approval info
        if 'approved' in vals and not vals['approved']:
            vals.update({
                'approved_by': False,
                'approved_date': False,
                'website_published': False  # Auto unpublish when rejected
            })

        return super().write(vals)

    @api.constrains('testimonial_date')
    def _check_testimonial_date(self):
        """Ensure testimonial date is not in the future"""
        for record in self:
            if record.testimonial_date and record.testimonial_date > fields.Date.today():
                raise models.ValidationError(_("Testimonial date cannot be in the future."))

    @api.constrains('rating')
    def _check_rating(self):
        """Ensure rating is valid"""
        for record in self:
            if record.rating and record.rating not in ['1', '2', '3', '4', '5']:
                raise models.ValidationError(_("Rating must be between 1 and 5 stars."))

    def unlink(self):
        """Override unlink to prevent deletion of approved testimonials"""
        approved_testimonials = self.filtered('approved')
        if approved_testimonials:
            raise models.UserError(_(
                "You cannot delete approved testimonials. "
                "Please reject them first or archive them instead."
            ))
        return super().unlink()

    @api.model
    def _get_default_service_type(self):
        """Get default service type if available"""
        service_type = self.env['service.type'].search([('active', '=', True)], limit=1)
        return service_type.id if service_type else False