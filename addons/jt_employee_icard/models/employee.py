from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    emp_id = fields.Char(
        string="Employee ID", 
        readonly=True, 
        copy=False, 
        default=lambda self: self.env['ir.sequence'].next_by_code('seqemp.seqemp') or 'New',
        help="Unique Employee ID generated automatically"
    )
    
    joined_date = fields.Date(string='Joined Date')
    expired_date = fields.Date(string='ID Card Expiry Date')
    
    @api.model
    def create(self, vals):
        """Enhanced create method with better ID generation"""
        if not vals.get('emp_id') or vals.get('emp_id') == 'New':
            vals['emp_id'] = self._generate_employee_id()
        return super(HrEmployee, self).create(vals)
    
    def write(self, vals):
        """Override write to auto-generate missing IDs"""
        result = super(HrEmployee, self).write(vals)
        
        # Auto-generate IDs for records that have 'New' or empty emp_id
        records_needing_id = self.filtered(lambda r: not r.emp_id or r.emp_id == 'New')
        if records_needing_id:
            for record in records_needing_id:
                try:
                    new_id = self._generate_employee_id()
                    # Use sudo() to bypass potential permission issues during auto-update
                    record.sudo().write({'emp_id': new_id})
                    _logger.info(f"Auto-generated Employee ID {new_id} for {record.name}")
                except Exception as e:
                    _logger.warning(f"Failed to auto-generate ID for {record.name}: {str(e)}")
        
        return result
    
    def _generate_employee_id(self):
        """Centralized method to generate employee IDs with fallback"""
        try:
            # Try to get next sequence number
            new_id = self.env['ir.sequence'].next_by_code('seqemp.seqemp')
            if new_id and new_id != 'New':
                return new_id
        except Exception as e:
            _logger.warning(f"Sequence generation failed: {str(e)}")
        
        # Fallback: Generate based on existing IDs
        try:
            existing_ids = self.search([('emp_id', '!=', False), ('emp_id', '!=', 'New')])
            if existing_ids:
                # Extract numbers from existing IDs and find the next one
                numbers = []
                for emp in existing_ids:
                    if emp.emp_id and emp.emp_id.startswith('EMP'):
                        try:
                            num = int(emp.emp_id[3:])  # Remove 'EMP' prefix
                            numbers.append(num)
                        except ValueError:
                            continue
                
                if numbers:
                    next_num = max(numbers) + 1
                    return f"EMP{next_num:05d}"
            
            # Ultimate fallback: Start from EMP00001
            return "EMP00001"
            
        except Exception as e:
            _logger.error(f"Fallback ID generation failed: {str(e)}")
            # Last resort: Use timestamp-based ID
            import time
            return f"EMP{int(time.time())}"
    
    def action_generate_employee_id(self):
        """Manual action to generate/regenerate employee ID"""
        if not self.emp_id or self.emp_id == 'New':
            try:
                new_id = self._generate_employee_id()
                self.write({'emp_id': new_id})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': f'Employee ID generated: {new_id}',
                        'sticky': False,
                        'type': 'success',
                    }
                }
            except Exception as e:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error',
                        'message': f'Failed to generate Employee ID: {str(e)}',
                        'sticky': True,
                        'type': 'danger',
                    }
                }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Info',
                    'message': f'Employee already has ID: {self.emp_id}',
                    'sticky': False,
                    'type': 'info',
                }
            }
    
    def action_bulk_generate_employee_ids(self):
        """Bulk action to generate IDs for multiple employees"""
        employees_needing_id = self.filtered(lambda r: not r.emp_id or r.emp_id == 'New')
        
        if not employees_needing_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Info',
                    'message': 'All selected employees already have Employee IDs',
                    'sticky': False,
                    'type': 'info',
                }
            }
        
        success_count = 0
        for employee in employees_needing_id:
            try:
                new_id = self._generate_employee_id()
                employee.write({'emp_id': new_id})
                success_count += 1
                _logger.info(f"Generated Employee ID {new_id} for {employee.name}")
            except Exception as e:
                _logger.error(f"Failed to generate ID for {employee.name}: {str(e)}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Generated Employee IDs for {success_count} employees',
                'sticky': False,
                'type': 'success',
            }
        }
    
    @api.model
    def _migrate_existing_employee_ids(self):
        """Data migration method - called during module upgrade"""
        _logger.info("Starting Employee ID migration for existing records...")
        
        # Find all employees with missing or 'New' IDs
        employees_needing_id = self.search([
            '|', 
            ('emp_id', '=', False), 
            ('emp_id', '=', 'New')
        ])
        
        if not employees_needing_id:
            _logger.info("No employees need ID migration")
            return
        
        _logger.info(f"Found {len(employees_needing_id)} employees needing ID migration")
        
        success_count = 0
        for employee in employees_needing_id:
            try:
                new_id = self._generate_employee_id()
                employee.sudo().write({'emp_id': new_id})
                success_count += 1
                _logger.info(f"Migrated Employee ID {new_id} for {employee.name}")
            except Exception as e:
                _logger.error(f"Migration failed for {employee.name}: {str(e)}")
        
        _logger.info(f"Employee ID migration completed. Success: {success_count}/{len(employees_needing_id)}")
    
    def action_print_idcard_enhanced(self):
        """Enhanced action to open the improved wizard (back functionality removed)"""
        return {
            'name': 'Print ID Card',
            'type': 'ir.actions.act_window',
            'res_model': 'print.employee.idcard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'active_model': 'hr.employee',
            }
        }
