# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cashfree_client_id = fields.Char(
        string='Cashfree Client ID',
        config_parameter='cashfree_payout.client_id',
    )
    cashfree_client_secret = fields.Char(
        string='Cashfree Client Secret',
        config_parameter='cashfree_payout.client_secret',
    )
    cashfree_environment = fields.Selection(
        selection=[('sandbox', 'Sandbox (Testing)'), ('production', 'Production')],
        string='Environment',
        config_parameter='cashfree_payout.environment',
        default='sandbox',
    )
    cashfree_payout_notify_email = fields.Char(
        string='Failure Notification Email',
        config_parameter='cashfree_payout.notify_email',
        help='Email address to notify when a payout transfer fails.',
    )
