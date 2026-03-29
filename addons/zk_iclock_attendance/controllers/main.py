# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import logging
from datetime import datetime, timedelta
from urllib.parse import unquote

_logger = logging.getLogger(__name__)


class ZKiClockController(http.Controller):
    """
    HTTP Controller for ZKTeco iClock Protocol
    
    Endpoints:
    - /iclock/cdata - Receive attendance and operational data
    - /iclock/getrequest - Device polling for commands
    - /iclock/devicecmd - Send commands to device
    """
    
    # Configuration for attendance rules
    DUPLICATE_PREVENTION_MINUTES = 2  # Anti-passback: Ignore punches within 2 minutes
    CHECKOUT_MIN_GAP_HOURS = 1  # Minimum hours between check-in and check-out
    GRACE_PERIOD_MINUTES = 15  # Grace period after shift start
    ROUNDING_MINUTES = 0  # Round to nearest X minutes (0 to disable)
    ENABLE_GAP_RULE = True  # Enable 1-hour gap rule (recommended)
    DEBUG_MODE = True  # Enable extensive logging
    
    @http.route('/iclock/cdata', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def iclock_cdata(self, **kwargs):
        """
        Handle attendance data and operational logs from device
        
        GET: Device initial connection (sends options, pushver, language)
        POST: Attendance data (ATTLOG) or operation logs (OPERLOG)
        """
        try:
            sn = kwargs.get('SN', '')
            
            if not sn:
                _logger.warning("iClock cdata request without Serial Number")
                return "OK"
            
            # Find device
            device = request.env['zk.device'].sudo().search([('serial_number', '=', sn)], limit=1)
            
            if not device:
                _logger.warning(f"Device with SN {sn} not found in Odoo")
                return "OK"
            
            # Update device last seen
            device.sudo().write({
                'last_connection': datetime.now(),
                'state': 'connected'
            })
            
            # Handle POST requests (actual data)
            if request.httprequest.method == 'POST':
                table = kwargs.get('table', '')
                
                if table == 'ATTLOG':
                    # Attendance data
                    self._process_attendance_data(device, request.httprequest.data.decode('utf-8', errors='ignore'))
                    
                elif table == 'OPERLOG':
                    # Operation logs
                    _logger.info(f"Device {sn}: Operation log received")
                    
                elif table == 'USER':
                    # User data
                    _logger.info(f"Device {sn}: User data received")
            
            return "OK"
            
        except Exception as e:
            _logger.error(f"Error in iclock_cdata: {str(e)}", exc_info=True)
            return "OK"
    
    @http.route('/iclock/getrequest', type='http', auth='none', methods=['GET'], csrf=False)
    def iclock_getrequest(self, **kwargs):
        """
        Device polling for commands
        
        Device sends this periodically to check if server has any commands
        """
        try:
            sn = kwargs.get('SN', '')
            
            if not sn:
                return "OK"
            
            # Find device
            device = request.env['zk.device'].sudo().search([('serial_number', '=', sn)], limit=1)
            
            if not device:
                return "OK"
            
            # Update device last seen
            device.sudo().write({
                'last_connection': datetime.now(),
                'state': 'connected'
            })
            
            # Check for pending commands
            commands = request.env['zk.device.command'].sudo().search([
                ('device_id', '=', device.id),
                ('state', '=', 'pending')
            ], order='create_date asc')
            
            if commands:
                # Return commands to device
                cmd_list = []
                for cmd in commands:
                    cmd_list.append(f"C:{cmd.id}:{cmd.command}")
                    cmd.sudo().write({'state': 'sent', 'sent_date': datetime.now()})
                
                return "\n".join(cmd_list)
            
            return "OK"
            
        except Exception as e:
            _logger.error(f"Error in iclock_getrequest: {str(e)}", exc_info=True)
            return "OK"
    
    @http.route('/iclock/devicecmd', type='http', auth='none', methods=['POST'], csrf=False)
    def iclock_devicecmd(self, **kwargs):
        """
        Device command response
        
        Device sends this after executing a command
        """
        try:
            sn = kwargs.get('SN', '')
            cmd_id = kwargs.get('ID', '')
            result = kwargs.get('Return', '')
            
            if cmd_id:
                command = request.env['zk.device.command'].sudo().browse(int(cmd_id))
                if command.exists():
                    command.sudo().write({
                        'state': 'completed' if result == 'OK' else 'failed',
                        'result': result,
                        'completed_date': datetime.now()
                    })
            
            return "OK"
            
        except Exception as e:
            _logger.error(f"Error in iclock_devicecmd: {str(e)}", exc_info=True)
            return "OK"
    
    def _is_duplicate_punch(self, employee_id, timestamp, attendance_obj):
        """
        Anti-Passback Rule: Check if this punch is a duplicate within time window
        
        Returns True if a punch exists within DUPLICATE_PREVENTION_MINUTES
        """
        if self.DUPLICATE_PREVENTION_MINUTES <= 0:
            return False
        
        time_window_start = timestamp - timedelta(minutes=self.DUPLICATE_PREVENTION_MINUTES)
        time_window_end = timestamp + timedelta(minutes=self.DUPLICATE_PREVENTION_MINUTES)
        
        # Check for any punch within the time window
        existing = attendance_obj.search([
            ('employee_id', '=', employee_id),
            '|',
            '&', ('check_in', '>=', time_window_start), ('check_in', '<=', time_window_end),
            '&', ('check_out', '>=', time_window_start), ('check_out', '<=', time_window_end)
        ], limit=1)
        
        return bool(existing)
    
    def _apply_rounding(self, dt):
        """
        Rounding Rule: Round datetime to nearest interval
        
        Example: If ROUNDING_MINUTES=15
        - 9:07 -> 9:00
        - 9:08 -> 9:15
        - 9:22 -> 9:15
        """
        if self.ROUNDING_MINUTES <= 0:
            return dt
        
        # Get minutes to round
        minutes = dt.minute
        seconds = dt.second
        
        # Calculate total seconds
        total_seconds = minutes * 60 + seconds
        
        # Round to nearest interval
        rounding_seconds = self.ROUNDING_MINUTES * 60
        rounded_seconds = round(total_seconds / rounding_seconds) * rounding_seconds
        
        # Create new datetime with rounded time
        rounded_dt = dt.replace(minute=0, second=0, microsecond=0)
        rounded_dt = rounded_dt + timedelta(seconds=rounded_seconds)
        
        return rounded_dt
    
    def _process_attendance_data(self, device, data):
        """
        Process attendance data from device with GAP RULE:
        
        NEW LOGIC:
        1. First punch of the day = Check-in
        2. Any punch after 1 hour (configurable) = Check-out
        3. Punches within 1 hour = Ignored as duplicates
        4. Multiple punches: First = check-in, Last (after 1hr) = check-out
        
        Format: PIN\tDateTime\tStatus\tVerify\tWorkCode\t\t\n
        Example: 1\t2026-01-10 13:00:00\t0\t1\t0\t\t\n
        
        Status: 0=Check-in, 1=Check-out, 2-4=Others (ignored by device)
        Verify: 0=Password, 1=Fingerprint, 2=Card, 15=Face, etc.
        """
        try:
            if not data or data.strip() == '':
                return
            
            _logger.info(f"{'='*80}")
            _logger.info(f"Device {device.serial_number}: Processing attendance with 1-HOUR GAP RULE")
            _logger.info(f"Raw data received:\n{data}")
            _logger.info(f"{'='*80}")
            
            lines = data.strip().split('\n')
            attendance_obj = request.env['hr.attendance'].sudo()
            employee_obj = request.env['hr.employee'].sudo()
            
            # Parse all punches first
            punches = []
            
            for line_num, line in enumerate(lines, 1):
                try:
                    if not line.strip():
                        continue
                    
                    if self.DEBUG_MODE:
                        _logger.info(f"Line {line_num}: {line}")
                    
                    # Parse line: PIN\tDateTime\tStatus\tVerify\tWorkCode
                    parts = line.split('\t')
                    
                    if len(parts) < 2:
                        _logger.warning(f"Invalid attendance line: {line}")
                        continue
                    
                    user_id = parts[0].strip()
                    timestamp_str = parts[1].strip()
                    status = parts[2].strip() if len(parts) > 2 else '0'
                    verify_type = parts[3].strip() if len(parts) > 3 else '1'
                    
                    if self.DEBUG_MODE:
                        _logger.info(f"  Parsed: user_id={user_id}, timestamp={timestamp_str}, status={status}")
                    
                    # Find employee
                    employee = employee_obj.search([('device_user_id', '=', user_id)], limit=1)
                    
                    if not employee:
                        _logger.warning(f"No employee found with device_user_id={user_id}")
                        continue
                    
                    if self.DEBUG_MODE:
                        _logger.info(f"  Found employee: {employee.name} (ID: {employee.id})")
                    
                    # Parse timestamp
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M')
                        except ValueError:
                            _logger.error(f"Could not parse timestamp: {timestamp_str}")
                            continue
                    
                    # Timezone conversion: Device time (IST) -> UTC
                    device_tz_str = 'Asia/Kolkata'
                    try:
                        import pytz
                        device_tz = pytz.timezone(device_tz_str)
                        local_dt = device_tz.localize(timestamp)
                        utc_dt = local_dt.astimezone(pytz.UTC)
                        timestamp_utc = utc_dt.replace(tzinfo=None)
                        
                        if self.DEBUG_MODE:
                            _logger.info(f"  Timezone: {timestamp_str} (IST) -> {timestamp_utc} (UTC)")
                        
                        timestamp = timestamp_utc
                    except Exception as tz_error:
                        _logger.warning(f"Timezone conversion error: {tz_error}. Using timestamp as-is.")
                    
                    punches.append({
                        'employee': employee,
                        'timestamp': timestamp,
                        'timestamp_str': timestamp_str,
                        'status': status,
                        'verify_type': verify_type,
                        'user_id': user_id
                    })
                    
                except Exception as line_error:
                    _logger.error(f"Error parsing line '{line}': {str(line_error)}", exc_info=True)
                    continue
            
            if not punches:
                _logger.info("No valid punches to process")
                return
            
            _logger.info(f"Total valid punches parsed: {len(punches)}")
            
            # Process punches with GAP RULE
            success_count = 0
            error_count = 0
            duplicate_count = 0
            
            if self.ENABLE_GAP_RULE:
                # GAP RULE: Check-out must be > 1 hour after check-in
                success, errors, duplicates = self._process_with_gap_rule(
                    punches, attendance_obj, device
                )
                success_count += success
                error_count += errors
                duplicate_count += duplicates
            else:
                # Fallback to FILO
                success, errors, duplicates = self._process_with_filo_rule(
                    punches, attendance_obj, device
                )
                success_count += success
                error_count += errors
                duplicate_count += duplicates
            
            _logger.info(f"{'='*80}")
            _logger.info(
                f"Processing Summary: {success_count} success, "
                f"{duplicate_count} duplicates ignored, {error_count} errors"
            )
            _logger.info(f"{'='*80}")
            
            # Update device stats
            device.sudo().write({
                'total_records_received': device.total_records_received + success_count
            })
            
        except Exception as e:
            _logger.error(f"Error processing attendance data: {str(e)}", exc_info=True)
    
    def _process_with_gap_rule(self, punches, attendance_obj, device):
        """
        GAP RULE: Punch after 1+ hour from check-in = Check-out
        
        Logic:
        1. No existing check-in for today → Create check-in
        2. Existing check-in + new punch > 1 hour later → Update with check-out
        3. Existing check-in + new punch < 1 hour later → Ignore (duplicate)
        4. Existing complete record (has check-out) → Ignore new punches
        """
        success_count = 0
        error_count = 0
        duplicate_count = 0
        
        _logger.info(f"\n{'='*80}")
        _logger.info(f"GAP RULE PROCESSING (Min gap: {self.CHECKOUT_MIN_GAP_HOURS} hour(s))")
        _logger.info(f"{'='*80}")
        
        # Sort all punches by timestamp (process in chronological order)
        punches.sort(key=lambda x: x['timestamp'])
        
        # Group by employee for processing
        from collections import defaultdict
        punches_by_employee = defaultdict(list)
        
        for punch in punches:
            employee_id = punch['employee'].id
            punches_by_employee[employee_id].append(punch)
        
        # Process each employee's punches
        for employee_id, emp_punches in punches_by_employee.items():
            try:
                employee_name = emp_punches[0]['employee'].name
                _logger.info(f"\n{'─'*80}")
                _logger.info(f"Processing: {employee_name}")
                _logger.info(f"Total punches: {len(emp_punches)}")
                
                # Process each punch individually
                for punch_idx, punch in enumerate(emp_punches, 1):
                    timestamp = punch['timestamp']
                    punch_date = timestamp.date()
                    
                    _logger.info(f"\n  Punch #{punch_idx}: {timestamp}")
                    
                    # Check for duplicate (within 2 minutes)
                    if self._is_duplicate_punch(employee_id, timestamp, attendance_obj):
                        _logger.info(f"    ⚠️  Ignored: Too close to existing punch (anti-passback)")
                        duplicate_count += 1
                        continue
                    
                    # Apply rounding
                    timestamp_rounded = self._apply_rounding(timestamp)
                    if timestamp != timestamp_rounded:
                        _logger.info(f"    Rounded: {timestamp} → {timestamp_rounded}")
                        timestamp = timestamp_rounded
                    
                    # Find any attendance record for this employee today
                    start_of_day = datetime.combine(punch_date, datetime.min.time())
                    end_of_day = start_of_day + timedelta(days=1)
                    
                    existing = attendance_obj.search([
                        ('employee_id', '=', employee_id),
                        ('check_in', '>=', start_of_day),
                        ('check_in', '<', end_of_day)
                    ], limit=1)
                    
                    if not existing:
                        # No attendance today → Create new check-in
                        _logger.info(f"    ✅ Creating CHECK-IN")
                        
                        try:
                            new_record = attendance_obj.create({
                                'employee_id': employee_id,
                                'check_in': timestamp,
                                'zk_device_id': device.id,
                            })
                            request.env.cr.commit()
                            
                            _logger.info(f"    ✅ Check-in created (ID: {new_record.id})")
                            success_count += 1
                            
                        except Exception as create_error:
                            _logger.error(f"    ❌ Failed to create: {str(create_error)}")
                            error_count += 1
                    
                    else:
                        # Existing attendance found
                        _logger.info(f"    Found existing record (ID: {existing.id})")
                        _logger.info(f"      Current check-in:  {existing.check_in}")
                        _logger.info(f"      Current check-out: {existing.check_out if existing.check_out else 'None'}")
                        
                        # If already has check-out, ignore this punch
                        if existing.check_out:
                            _logger.info(f"    ⚠️  Ignored: Already has check-out")
                            duplicate_count += 1
                            continue
                        
                        # Calculate time gap from check-in
                        time_gap = timestamp - existing.check_in
                        hours_gap = time_gap.total_seconds() / 3600
                        
                        _logger.info(f"      Time gap: {hours_gap:.2f} hours")
                        
                        # GAP RULE: Check if gap is sufficient for check-out
                        if hours_gap >= self.CHECKOUT_MIN_GAP_HOURS:
                            _logger.info(f"    ✅ Gap sufficient ({hours_gap:.2f}h >= {self.CHECKOUT_MIN_GAP_HOURS}h)")
                            _logger.info(f"    📝 Updating with CHECK-OUT")
                            
                            try:
                                existing.sudo().write({'check_out': timestamp})
                                request.env.cr.commit()
                                
                                # Verify update
                                existing.sudo().invalidate_cache()
                                refreshed = attendance_obj.browse(existing.id)
                                
                                if refreshed.check_out:
                                    duration = refreshed.check_out - refreshed.check_in
                                    duration_hours = duration.total_seconds() / 3600
                                    
                                    _logger.info(f"    ✅ Check-out updated successfully!")
                                    _logger.info(f"      Check-in:  {refreshed.check_in}")
                                    _logger.info(f"      Check-out: {refreshed.check_out}")
                                    _logger.info(f"      Duration:  {duration_hours:.2f} hours")
                                    success_count += 1
                                else:
                                    _logger.error(f"    ❌ Check-out not saved (verification failed)")
                                    error_count += 1
                                    
                            except Exception as update_error:
                                _logger.error(f"    ❌ Failed to update: {str(update_error)}")
                                error_count += 1
                        else:
                            _logger.info(f"    ⚠️  Ignored: Gap too small ({hours_gap:.2f}h < {self.CHECKOUT_MIN_GAP_HOURS}h)")
                            _logger.info(f"    This prevents accidental double-taps from being check-out")
                            duplicate_count += 1
                
            except Exception as e:
                _logger.error(f"❌ Error processing employee {employee_id}: {str(e)}", exc_info=True)
                error_count += 1
        
        _logger.info(f"\n{'='*80}")
        _logger.info("GAP RULE PROCESSING COMPLETE")
        _logger.info(f"{'='*80}\n")
        
        return success_count, error_count, duplicate_count
    
    def _process_with_filo_rule(self, punches, attendance_obj, device):
        """
        FALLBACK: FILO Rule - First punch = Check-In, Last punch = Check-Out
        Used when GAP RULE is disabled
        """
        success_count = 0
        error_count = 0
        duplicate_count = 0
        
        from collections import defaultdict
        punches_by_employee_date = defaultdict(list)
        
        _logger.info(f"\n{'='*80}")
        _logger.info("FILO PROCESSING (FALLBACK)")
        _logger.info(f"{'='*80}")
        
        for punch in punches:
            employee_id = punch['employee'].id
            punch_date = punch['timestamp'].date()
            key = (employee_id, punch_date)
            punches_by_employee_date[key].append(punch)
        
        for (employee_id, punch_date), day_punches in punches_by_employee_date.items():
            try:
                employee_name = day_punches[0]['employee'].name
                day_punches.sort(key=lambda x: x['timestamp'])
                
                filtered_punches = []
                for punch in day_punches:
                    if not self._is_duplicate_punch(employee_id, punch['timestamp'], attendance_obj):
                        filtered_punches.append(punch)
                    else:
                        duplicate_count += 1
                
                if not filtered_punches:
                    continue
                
                first_punch = filtered_punches[0]
                last_punch = filtered_punches[-1] if len(filtered_punches) > 1 else None
                
                check_in_time = self._apply_rounding(first_punch['timestamp'])
                check_out_time = self._apply_rounding(last_punch['timestamp']) if last_punch else None
                
                start_of_day = datetime.combine(punch_date, datetime.min.time())
                end_of_day = start_of_day + timedelta(days=1)
                
                existing = attendance_obj.search([
                    ('employee_id', '=', employee_id),
                    ('check_in', '>=', start_of_day),
                    ('check_in', '<', end_of_day)
                ], limit=1)
                
                if existing:
                    if check_out_time and check_out_time != check_in_time:
                        update_vals = {}
                        if check_in_time < existing.check_in:
                            update_vals['check_in'] = check_in_time
                        if not existing.check_out or check_out_time > existing.check_out:
                            update_vals['check_out'] = check_out_time
                        
                        if update_vals:
                            existing.sudo().write(update_vals)
                            request.env.cr.commit()
                            success_count += 1
                else:
                    attendance_data = {
                        'employee_id': employee_id,
                        'check_in': check_in_time,
                        'zk_device_id': device.id,
                    }
                    if check_out_time and check_out_time != check_in_time:
                        attendance_data['check_out'] = check_out_time
                    
                    attendance_obj.create(attendance_data)
                    request.env.cr.commit()
                    success_count += 1
                
            except Exception as e:
                _logger.error(f"Error in FILO for employee {employee_id}: {str(e)}", exc_info=True)
                error_count += 1
        
        return success_count, error_count, duplicate_count
