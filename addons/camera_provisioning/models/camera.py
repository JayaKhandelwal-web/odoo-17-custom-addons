# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CctvCamera(models.Model):
    _name = 'cctv.camera'
    _description = 'CCTV Camera'
    _order = 'name'

    name = fields.Char(string='Camera Name', required=True)
    mac_address = fields.Char(string='MAC Address', help='Bluetooth MAC Address')
    serial_number = fields.Char(string='Serial Number')
    
    # Network Info
    ip_address = fields.Char(string='IP Address', help='Camera IP on local network')
    router_ddns = fields.Char(string='Router DDNS', help='MikroTik Cloud DDNS address')
    external_port = fields.Integer(string='External Port', default=8554)
    
    # RTSP Settings
    rtsp_port = fields.Integer(string='RTSP Port', default=554)
    rtsp_path = fields.Char(string='RTSP Path', default='/stream1')
    rtsp_username = fields.Char(string='RTSP Username', default='admin')
    rtsp_password = fields.Char(string='RTSP Password', default='admin')
    
    # WiFi Provisioning
    wifi_ssid = fields.Char(string='WiFi SSID')
    wifi_configured = fields.Boolean(string='WiFi Configured', default=False)
    provisioning_date = fields.Datetime(string='Provisioning Date')
    
    # Location
    location = fields.Selection([
        ('office', 'Office'),
        ('bus_stand', 'Bus Stand'),
        ('parking', 'Parking'),
        ('entrance', 'Entrance'),
        ('other', 'Other'),
    ], string='Location Type', default='office')
    location_name = fields.Char(string='Location Name')
    
    # Status
    state = fields.Selection([
        ('new', 'New'),
        ('provisioning', 'Provisioning'),
        ('configured', 'Configured'),
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error'),
    ], string='Status', default='new')
    
    last_seen = fields.Datetime(string='Last Seen')
    notes = fields.Text(string='Notes')
    
    # Computed Fields
    rtsp_url = fields.Char(string='RTSP URL', compute='_compute_rtsp_url')
    rtsp_external_url = fields.Char(string='External RTSP URL', compute='_compute_rtsp_url')
    
    @api.depends('ip_address', 'rtsp_port', 'rtsp_path', 'rtsp_username', 'rtsp_password', 
                 'router_ddns', 'external_port')
    def _compute_rtsp_url(self):
        for record in self:
            # Local URL
            if record.ip_address:
                auth = ''
                if record.rtsp_username and record.rtsp_password:
                    auth = f'{record.rtsp_username}:{record.rtsp_password}@'
                record.rtsp_url = f'rtsp://{auth}{record.ip_address}:{record.rtsp_port}{record.rtsp_path}'
            else:
                record.rtsp_url = False
            
            # External URL (via router DDNS)
            if record.router_ddns:
                auth = ''
                if record.rtsp_username and record.rtsp_password:
                    auth = f'{record.rtsp_username}:{record.rtsp_password}@'
                record.rtsp_external_url = f'rtsp://{auth}{record.router_ddns}:{record.external_port}{record.rtsp_path}'
            else:
                record.rtsp_external_url = False
    
    def action_provision_wifi(self):
        """Open WiFi provisioning wizard"""
        return {
            'name': 'Provision Camera WiFi',
            'type': 'ir.actions.act_window',
            'res_model': 'cctv.camera.provision.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_camera_id': self.id},
        }
    
    def action_test_connection(self):
        """Test RTSP connection (placeholder - actual test done via JS)"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'camera_test_connection',
            'params': {'camera_id': self.id},
        }


class CctvCameraProvisionWizard(models.TransientModel):
    _name = 'cctv.camera.provision.wizard'
    _description = 'Camera WiFi Provisioning Wizard'
    
    camera_id = fields.Many2one('cctv.camera', string='Camera')
    wifi_ssid = fields.Char(string='WiFi SSID', required=True)
    wifi_password = fields.Char(string='WiFi Password', required=True)
    
    def action_provision(self):
        """This triggers the JavaScript BLE provisioning"""
        return {
            'type': 'ir.actions.client',
            'tag': 'camera_ble_provision',
            'params': {
                'camera_id': self.camera_id.id,
                'wifi_ssid': self.wifi_ssid,
                'wifi_password': self.wifi_password,
            },
        }
