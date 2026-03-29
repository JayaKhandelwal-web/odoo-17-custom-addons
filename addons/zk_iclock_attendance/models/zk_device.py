# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import requests
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class ZkDevice(models.Model):
    _name = 'zk.device'
    _description = 'ZKTeco Biometric Device'
    _order = 'name'
    
    name = fields.Char('Device Name', required=True, help="Friendly name for this device")
    serial_number = fields.Char(
        'Serial Number', 
        required=True, 
        help="Device Serial Number (SN) - must match device settings"
    )
    location = fields.Char('Location', help="Physical location of the device")
    
    state = fields.Selection([
        ('draft', 'Not Connected'),
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
        ('error', 'Error')
    ], string='Status', default='draft')
    
    last_connection = fields.Datetime('Last Connection', readonly=True)
    total_records_received = fields.Integer('Total Records Received', default=0, readonly=True)
    
    # Network configuration
    server_url = fields.Char('Server URL', compute='_compute_server_url', store=False)
    server_port = fields.Integer('Server Port', compute='_compute_server_port', store=False)
    
    # Device info
    firmware_version = fields.Char('Firmware Version', readonly=True)
    device_model = fields.Char('Device Model', readonly=True)
    
    # Relationships
    employee_ids = fields.Many2many(
        'hr.employee', 
        string='Assigned Employees',
        compute='_compute_employee_ids'
    )
    employee_count = fields.Integer('Employee Count', compute='_compute_employee_count')
    
    command_ids = fields.One2many('zk.device.command', 'device_id', string='Commands')
    pending_command_count = fields.Integer('Pending Commands', compute='_compute_pending_commands')
    
    notes = fields.Text('Notes')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    active = fields.Boolean('Active', default=True)
    
    _sql_constraints = [
        ('serial_number_unique', 'unique(serial_number)', 'Serial Number must be unique!')
    ]
    
    @api.depends('serial_number')
    def _compute_server_url(self):
        """Compute the server URL for device configuration"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for device in self:
            # Remove port from URL if present
            if ':' in base_url and not base_url.startswith('https://'):
                url_parts = base_url.split(':')
                device.server_url = ':'.join(url_parts[:-1]).replace('http://', '').replace('https://', '')
            else:
                device.server_url = base_url.replace('http://', '').replace('https://', '')
    
    @api.depends('serial_number')
    def _compute_server_port(self):
        """Compute the server port for device configuration"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for device in self:
            if 'https://' in base_url:
                device.server_port = 443
            elif ':' in base_url:
                try:
                    device.server_port = int(base_url.split(':')[-1].split('/')[0])
                except:
                    device.server_port = 80
            else:
                device.server_port = 80
    
    @api.depends('serial_number')
    def _compute_employee_ids(self):
        """Get all employees assigned to this device"""
        for device in self:
            device.employee_ids = self.env['hr.employee'].search([
                ('zk_device_id', '=', device.id)
            ])
    
    @api.depends('employee_ids')
    def _compute_employee_count(self):
        """Count employees assigned to device"""
        for device in self:
            device.employee_count = len(device.employee_ids)
    
    @api.depends('command_ids.state')
    def _compute_pending_commands(self):
        """Count pending commands"""
        for device in self:
            device.pending_command_count = len(device.command_ids.filtered(lambda c: c.state == 'pending'))
    
    def action_view_employees(self):
        """Open employee list for this device"""
        self.ensure_one()
        return {
            'name': _('Device Employees'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'domain': [('zk_device_id', '=', self.id)],
            'context': {'default_zk_device_id': self.id}
        }
    
    def action_view_attendance(self):
        """View attendance from this device"""
        self.ensure_one()
        return {
            'name': _('Device Attendance'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'tree,form',
            'domain': [('zk_device_id', '=', self.id)],
            'context': {'default_zk_device_id': self.id}
        }
    
    def action_show_configuration(self):
        """Show device configuration guide"""
        self.ensure_one()
        
        message = f"""
        <div class="container">
            <h3>Device Configuration Guide</h3>
            <p>Configure your {self.name} with these settings:</p>
            
            <h4>On Device: Menu → Comm → Cloud Server (or ADMS)</h4>
            <table class="table">
                <tr>
                    <td><b>Serial Number:</b></td>
                    <td><code>{self.serial_number}</code></td>
                </tr>
                <tr>
                    <td><b>Server Address:</b></td>
                    <td><code>{self.server_url}</code></td>
                </tr>
                <tr>
                    <td><b>Server Port:</b></td>
                    <td><code>{self.server_port}</code></td>
                </tr>
                <tr>
                    <td><b>Communication Mode:</b></td>
                    <td>Push/Auto</td>
                </tr>
            </table>
            
            <h4>Device Endpoints:</h4>
            <ul>
                <li>Attendance Data: <code>/iclock/cdata</code></li>
                <li>Commands: <code>/iclock/getrequest</code></li>
            </ul>
            
            <h4>Next Steps:</h4>
            <ol>
                <li>Apply settings on device</li>
                <li>Restart device</li>
                <li>Device should connect within 1-2 minutes</li>
                <li>Status will change to "Connected"</li>
            </ol>
            
            <div class="alert alert-info">
                <p><b>Troubleshooting:</b></p>
                <ul>
                    <li>Ensure device WiFi is connected</li>
                    <li>Verify Serial Number matches exactly</li>
                    <li>Check firewall allows port {self.server_port}</li>
                    <li>Device should be in "Push" or "Auto" mode</li>
                </ul>
            </div>
        </div>
        """
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Device Configuration'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }
    
    def action_sync_employees(self):
        """Sync employees to device (push all employees)"""
        self.ensure_one()
        
        employees = self.env['hr.employee'].search([
            ('zk_device_id', '=', self.id),
            ('device_user_id', '!=', False)
        ])
        
        if not employees:
            raise UserError(_('No employees assigned to this device!'))
        
        # Create DATA command to upload users
        user_data = []
        for emp in employees:
            # Format: PIN=1\tName=Employee Name\tPri=0\tPasswd=\tCard=\t\n
            user_data.append(f"PIN={emp.device_user_id}\tName={emp.name}\tPri=0\tPasswd=\tCard=")
        
        self.env['zk.device.command'].create({
            'device_id': self.id,
            'command': 'DATA UPDATE USERINFO\t' + '\n'.join(user_data),
            'name': 'Sync All Employees',
            'state': 'pending'
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Employee sync command queued. {len(employees)} employees will be pushed to device.',
                'type': 'success',
            }
        }
    
    def action_clear_attendance(self):
        """Clear attendance data from device"""
        self.ensure_one()
        
        self.env['zk.device.command'].create({
            'device_id': self.id,
            'command': 'DATA DELETE ATTLOG',
            'name': 'Clear Attendance Data',
            'state': 'pending'
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Clear attendance command sent to device.',
                'type': 'warning',
            }
        }
    
    def action_restart_device(self):
        """Restart device remotely"""
        self.ensure_one()
        
        self.env['zk.device.command'].create({
            'device_id': self.id,
            'command': 'RESTART',
            'name': 'Restart Device',
            'state': 'pending'
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Restart command sent to device.',
                'type': 'info',
            }
        }
    
    @api.model
    def cron_check_device_status(self):
        """Cron job to check device connection status"""
        devices = self.search([('state', '=', 'connected')])
        
        for device in devices:
            if device.last_connection:
                time_diff = datetime.now() - device.last_connection
                
                # If no connection in 5 minutes, mark as disconnected
                if time_diff > timedelta(minutes=5):
                    device.write({'state': 'disconnected'})
                    _logger.warning(f"Device {device.name} ({device.serial_number}) is disconnected")


class ZkDeviceCommand(models.Model):
    _name = 'zk.device.command'
    _description = 'ZKTeco Device Command'
    _order = 'create_date desc'
    
    device_id = fields.Many2one('zk.device', string='Device', required=True, ondelete='cascade')
    name = fields.Char('Command Name', required=True)
    command = fields.Text('Command', required=True)
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='pending', string='Status')
    
    create_date = fields.Datetime('Created', readonly=True)
    sent_date = fields.Datetime('Sent Date', readonly=True)
    completed_date = fields.Datetime('Completed Date', readonly=True)
    
    result = fields.Text('Result', readonly=True)
