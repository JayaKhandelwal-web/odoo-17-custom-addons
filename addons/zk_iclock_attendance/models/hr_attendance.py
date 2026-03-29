# -*- coding: utf-8 -*-

from odoo import models, fields


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    
    zk_device_id = fields.Many2one(
        'zk.device',
        string='Source Device',
        readonly=True,
        help='Biometric device that recorded this attendance'
    )
