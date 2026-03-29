# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ClientLogo(models.Model):
    _name = 'annapurna.client.logo'
    _description = 'Client Logo for Website Display'
    _order = 'sequence, name'

    name = fields.Char(string='Client Name', required=True)
    logo = fields.Image(string='Client Logo', required=True, max_width=400, max_height=400)
    sequence = fields.Integer(string='Sequence', default=10, help='Display order on website')
    website_url = fields.Char(string='Website URL', help='Client website URL (optional)')
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')

    # For tracking
    create_date = fields.Datetime(string='Created on', readonly=True)
    write_date = fields.Datetime(string='Last Updated on', readonly=True)

    @api.constrains('logo')
    def _check_logo(self):
        for record in self:
            if not record.logo:
                raise ValidationError("Client logo is required!")