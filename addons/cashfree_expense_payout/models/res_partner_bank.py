# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartnerBank(models.Model):
    """
    Store Cashfree bank verification result on the bank account itself,
    so it persists across all expense reports for the same employee.
    """
    _inherit = 'res.partner.bank'

    cashfree_bank_verified = fields.Selection(
        selection=[
            ('not_verified', 'Not Verified'),
            ('verified', 'Verified'),
            ('failed', 'Verification Failed'),
        ],
        string='Cashfree Bank Verification',
        default='not_verified',
        readonly=True, copy=False,
        help='Verification status via Cashfree. Once verified, no re-verification needed.',
    )
    cashfree_verified_name = fields.Char(
        string='Verified Name at Bank',
        readonly=True, copy=False,
    )
    cashfree_verify_message = fields.Char(
        string='Cashfree Verification Message',
        readonly=True, copy=False,
    )
