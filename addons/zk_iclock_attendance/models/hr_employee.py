# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging
from datetime import timedelta
import pytz

_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    device_user_id = fields.Char(
        'Device User ID',
        help='Unique ID in biometric device (must be numeric). Links employee to fingerprint in device.'
    )
    
    zk_device_id = fields.Many2one(
        'zk.device',
        string='Biometric Device',
        help='ZKTeco device this employee is registered on'
    )
    
    synced_to_device = fields.Boolean('Synced to Device', default=False, readonly=True)
    last_sync_date = fields.Datetime('Last Sync Date', readonly=True)
    
    # NEW FIELD: Track if notification was sent today
    last_absent_notification_date = fields.Date(
        'Last Absent Notification', 
        readonly=True, 
        help="Prevents sending multiple absent notifications on the same day."
    )
    
    _sql_constraints = [
        ('device_user_id_unique', 'unique(device_user_id)', 
         'Device User ID must be unique! Each employee needs a unique ID.')
    ]
    
    @api.model
    def _cron_check_absent_employees(self):
        """Cron job to check for biometric employees absent > 30 mins after shift start"""
        _logger.info("Starting absent biometric employee check...")
        today = fields.Date.today()
        now_utc = pytz.utc.localize(fields.Datetime.now())

        # Find active BIOMETRIC employees who haven't been notified today
        employees = self.search([
            ('active', '=', True),
            ('device_user_id', '!=', False),  # Must be registered on biometric device
            ('zk_device_id', '!=', False),    # Must be linked to a device
#            '|', 
#            ('last_absent_notification_date', '!=', today), 
#            ('last_absent_notification_date', '=', False)
        ])

        # Track absent employees to process after the loop
        absent_employees = self.env['hr.employee']
        absent_names = []

        for emp in employees:
            # Skip if they have no working schedule assigned
            if not emp.resource_calendar_id:
                continue 

            # Calculate employee's local timezone
            tz = pytz.timezone(emp.tz or self.env.user.tz or 'UTC')
            local_now = now_utc.astimezone(tz)
            start_of_day = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = local_now.replace(hour=23, minute=59, second=59, microsecond=0)

            # Get working intervals for today based on the employee's calendar
            intervals = emp.resource_calendar_id._work_intervals_batch(
                start_of_day, end_of_day, resources=emp.resource_id, tz=tz
            )

            # Skip if employee is not scheduled to work today
            if not intervals or not intervals.get(emp.resource_id.id):
                continue 

            # Convert the special WorkIntervals object into a standard list first
            emp_intervals_list = list(intervals[emp.resource_id.id])
            
            # Get the earliest shift start time today (tz-aware UTC datetime)
            shift_start_utc = emp_intervals_list[0][0]

            # If 30 minutes haven't passed since their specific shift start, skip
            if now_utc < (shift_start_utc + timedelta(minutes=30)):
                continue

            # Check if they have an attendance check-in for today
            attendance = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', start_of_day.astimezone(pytz.utc).replace(tzinfo=None))
            ], limit=1)

            # If no attendance found, they are absent. Add them to our list!
            if not attendance:
                absent_employees |= emp  # Add to Odoo recordset
                absent_names.append(emp.name) # Add to name list
        
        # After checking everyone, see if we found anyone absent
        if absent_names:
            _logger.info(f"Found {len(absent_names)} absent employees. Sending consolidated message...")
            
            # Join all names into a single string (e.g., "Raja, Amit, John")
            names_string = ", ".join(absent_names)
            
            success = self._send_consolidated_absent_whatsapp_notification(names_string)
            if success:
                # Update tracking field for ALL absent employees at once
                absent_employees.write({'last_absent_notification_date': today})
        else:
            _logger.info("No absent biometric employees found.")

    def _send_consolidated_absent_whatsapp_notification(self, names_string):
        """Sends the 'absent' template to multiple hardcoded numbers with all names"""
        
        # Hardcoded target numbers
        target_numbers = [
            {"countryCode": "+91", "phoneNumber": "9669155200"},
            {"countryCode": "+91", "phoneNumber": "9827054100"},
            {"countryCode": "+91", "phoneNumber": "8298913646"}
        ]

        # Interakt API Configuration
        api_key = "NG5EZVhCTmgtN0JNWjVIWVVLMGpSTjFDNDQxSUJ4bi1yN3BsOXI0T1gxczo="
        
        # Because we are sending multiple names, we must use the generic fallback image
        header_image_url = "https://interaktprodmediastorage.blob.core.windows.net/mediaprodstoragecontainer/d609fe61-1955-4a98-9f1d-6a2b83f9b915/message_template_media/fJXzYvzIJZRu/Gemini_Generated_Image_giqg6kgiqg6kgiqg.png?se=2031-02-09T09%3A24%3A55Z&sp=rt&sv=2019-12-12&sr=b&sig=Yb69kuZbLAc8tnQb6Uw2Tz6njtYo%2BVEeOuT1%2BrEAghY%3D"

        headers = {
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json"
        }
        interakt_base_url = "https://api.interakt.ai/v1"

        # Template variables for {{1}} and {{2}}
        date_str = fields.Date.today().strftime('%d-%b-%Y')
        reason_or_date = f"unreported absences on {date_str}"

        any_success = False

        # Loop through each target number and send the message
        for target in target_numbers:
            message_payload = {
                "countryCode": target["countryCode"],
                "phoneNumber": target["phoneNumber"],
                "callbackData": "consolidated_absent_notification",
                "type": "Template",
                "template": {
                    "name": "absent",
                    "languageCode": "en",
                    "headerValues": [header_image_url],
                    # {{1}} will now be replaced with "Raja, Amit, John..."
                    "bodyValues": [names_string, reason_or_date]
                }
            }

            try:
                response = requests.post(
                    f"{interakt_base_url}/public/message/",
                    headers=headers,
                    json=message_payload,
                    timeout=10
                )
                if response.ok:
                    _logger.info(f"✅ Consolidated absent notification sent successfully to {target['phoneNumber']}")
                    any_success = True
                else:
                    _logger.error(f"❌ Failed to send WA to {target['phoneNumber']}: {response.text}")
            except Exception as e:
                _logger.error(f"❌ WA API Error for {target['phoneNumber']}: {str(e)}")

        # Returns True if at least ONE message sent successfully, so the date updates
        return any_success

    def action_push_to_device(self):
        """Push single employee to device"""
        self.ensure_one()
        
        if not self.device_user_id:
            raise UserError(_('Please set Device User ID first!'))
        
        if not self.zk_device_id:
            raise UserError(_('Please assign a Biometric Device first!'))
        
        # Create command to add user to device
        user_data = f"PIN={self.device_user_id}\tName={self.name}\tPri=0\tPasswd=\tCard="
        
        self.env['zk.device.command'].create({
            'device_id': self.zk_device_id.id,
            'command': f'DATA UPDATE USERINFO\t{user_data}',
            'name': f'Add User: {self.name}',
            'state': 'pending'
        })
        
        self.write({
            'synced_to_device': True,
            'last_sync_date': fields.Datetime.now()
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'{self.name} queued to be pushed to device.',
                'type': 'success',
            }
        }
    
    def action_delete_from_device(self):
        """Delete employee from device"""
        self.ensure_one()
        
        if not self.device_user_id or not self.zk_device_id:
            return
        
        # Create command to delete user from device
        self.env['zk.device.command'].create({
            'device_id': self.zk_device_id.id,
            'command': f'DATA DELETE USERINFO PIN={self.device_user_id}',
            'name': f'Delete User: {self.name}',
            'state': 'pending'
        })
        
        self.write({
            'synced_to_device': False,
            'last_sync_date': False
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'{self.name} deletion queued on device.',
                'type': 'warning',
            }
        }
    
    def action_bulk_push_to_device(self):
        """Push multiple employees to device"""
        success_count = 0
        error_list = []
        
        for employee in self:
            try:
                if not employee.device_user_id:
                    error_list.append(f"{employee.name}: No Device User ID")
                    continue
                
                if not employee.zk_device_id:
                    error_list.append(f"{employee.name}: No Device Assigned")
                    continue
                
                employee.action_push_to_device()
                success_count += 1
                
            except Exception as e:
                error_list.append(f"{employee.name}: {str(e)}")
        
        message = f'✓ {success_count} employees queued for sync'
        if error_list:
            message += f'\n⚠ {len(error_list)} errors: ' + ', '.join(error_list[:3])
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success' if not error_list else 'warning',
                'sticky': True,
            }
        }
