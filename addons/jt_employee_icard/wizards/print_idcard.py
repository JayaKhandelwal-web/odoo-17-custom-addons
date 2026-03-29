from odoo import models, fields, api
import logging
import json

_logger = logging.getLogger(__name__)

class PrintEmployeeIDCard(models.TransientModel):
    _name = 'print.employee.idcard'
    _description = 'Print Employee ID Card'
    _transient_max_hours = 24  # Increase timeout for multi-employee sessions
    
    # Multi-employee support
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    current_employee_id = fields.Many2one('hr.employee', string='Current Employee')
    employee_index = fields.Integer(default=0)
    total_employees = fields.Integer(compute='_compute_total_employees')
    
    # Template selection - Square theme as default and main
    template_type = fields.Selection([
        ('square', 'Square Theme'),
    ], string='Template Design', required=True, default='square')
    
    # Editable fields for wizard (can override employee data)
    employee_name = fields.Char(string='Employee Name', required=True)
    employee_job = fields.Char(string='Job Position')
    employee_phone = fields.Char(string='Phone')
    employee_barcode = fields.Char(string='Employee ID')
    employee_image = fields.Image(string='Employee Photo', max_width=1920, max_height=1920)
    company_name = fields.Char(string='Company Name')
    
    # JSON storage for wizard data persistence
    wizard_data = fields.Text(string='Wizard Data Storage', default='{}')
    
    @api.depends('employee_ids')
    def _compute_total_employees(self):
        for record in self:
            record.total_employees = len(record.employee_ids)
    
    @api.model
    def default_get(self, fields_list):
        """Enhanced default_get with multi-employee support"""
        res = super().default_get(fields_list)
        context = self.env.context
        
        if context.get('active_ids'):
            employee_ids = context.get('active_ids')
            res['employee_ids'] = [(6, 0, employee_ids)]
            if employee_ids:
                res['current_employee_id'] = employee_ids[0]
                res['employee_index'] = 0
                # Load current employee data
                employee = self.env['hr.employee'].browse(employee_ids[0])
                if employee.exists():
                    res.update(self._load_employee_data(employee))
        elif context.get('active_id'):
            # Single employee from context
            employee_id = context.get('active_id')
            res['employee_ids'] = [(6, 0, [employee_id])]
            res['current_employee_id'] = employee_id
            res['employee_index'] = 0
            employee = self.env['hr.employee'].browse(employee_id)
            if employee.exists():
                res.update(self._load_employee_data(employee))
        
        return res
    
    def _load_employee_data(self, employee):
        """Smart data loading - combines employee data with wizard overrides"""
        if not employee.exists():
            return {}
            
        data = {
            'employee_name': employee.name or '',
            'employee_job': employee.job_id.name if employee.job_id else '',
            'employee_phone': employee.work_phone or employee.mobile_phone or '',
            'employee_barcode': employee.emp_id or employee.barcode or employee.identification_id or str(employee.id),
            'employee_image': employee.image_1920,
            'company_name': employee.company_id.name if employee.company_id else 'Your Company Name',
        }
        
        # Load wizard-specific data from storage
        try:
            wizard_storage = json.loads(self.wizard_data or '{}')
            employee_data = wizard_storage.get(str(employee.id), {})
            
            # Template type is always square (main theme)
            data['template_type'] = 'square'
            
            # Override with wizard data if available
            for field in ['employee_name', 'employee_job', 'employee_phone', 'employee_barcode', 'company_name']:
                if employee_data.get(field.replace('employee_', '')):
                    data[field] = employee_data.get(field.replace('employee_', ''))
                    
        except Exception as e:
            _logger.warning("Error loading wizard data: %s" % str(e))
        
        return data
    
    def _save_wizard_data(self):
        """JSON-based wizard data storage for persistence"""
        if not self.current_employee_id:
            return
            
        try:
            wizard_storage = json.loads(self.wizard_data or '{}')
        except:
            wizard_storage = {}
        
        employee_data = {
            'name': self.employee_name,
            'job': self.employee_job,
            'company_name': self.company_name,
            'phone': self.employee_phone,
            'barcode': self.employee_barcode,
            'template_type': 'square',  # Always square theme
            'image': self.employee_image.decode() if self.employee_image else None,
        }
        
        wizard_storage[str(self.current_employee_id.id)] = employee_data
        self.wizard_data = json.dumps(wizard_storage)
    
    @api.onchange('current_employee_id')
    def _onchange_current_employee(self):
        """Auto-load data when employee changes"""
        if self.current_employee_id and self.current_employee_id.exists():
            data = self._load_employee_data(self.current_employee_id)
            for field, value in data.items():
                if hasattr(self, field):
                    setattr(self, field, value)
    
    @api.onchange('employee_name', 'employee_job', 'company_name', 
                  'employee_phone', 'employee_barcode', 'employee_image', 'template_type')
    def _onchange_employee_fields(self):
        """Auto-save functionality on field changes"""
        self._save_wizard_data()
    
    def action_previous_employee(self):
        """Navigate to previous employee"""
        if self.employee_index > 0:
            self._save_wizard_data()
            self._save_current_employee_changes()
            self.employee_index -= 1
            self.current_employee_id = self.employee_ids[self.employee_index]
            if self.current_employee_id.exists():
                data = self._load_employee_data(self.current_employee_id)
                for field, value in data.items():
                    if hasattr(self, field):
                        setattr(self, field, value)
        return self._reload_wizard()
    
    def action_next_employee(self):
        """Navigate to next employee"""
        if self.employee_index < len(self.employee_ids) - 1:
            self._save_wizard_data()
            self._save_current_employee_changes()
            self.employee_index += 1
            self.current_employee_id = self.employee_ids[self.employee_index]
            if self.current_employee_id.exists():
                data = self._load_employee_data(self.current_employee_id)
                for field, value in data.items():
                    if hasattr(self, field):
                        setattr(self, field, value)
        return self._reload_wizard()
    
    def _save_current_employee_changes(self):
        """Save changes back to employee record"""
        if not self.current_employee_id or not self.current_employee_id.exists():
            return
            
        try:
            job_id = False
            if self.employee_job:
                job = self.env['hr.job'].search([('name', '=', self.employee_job)], limit=1)
                if not job:
                    job = self.env['hr.job'].create({'name': self.employee_job})
                job_id = job.id
            
            values = {
                'name': self.employee_name,
                'job_id': job_id,
                'work_phone': self.employee_phone,
                'emp_id': self.employee_barcode,
                'image_1920': self.employee_image,
            }
            
            self.current_employee_id.write(values)
            _logger.info(f"Updated employee {self.current_employee_id.name}")
            
        except Exception as e:
            _logger.error(f"Error saving employee: {str(e)}")
    
    def _reload_wizard(self):
        """Reload wizard to refresh view"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }
    
    def action_save_changes(self):
        """Manually save changes"""
        self._save_wizard_data()
        self._save_current_employee_changes()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Employee data saved successfully!',
                'sticky': False,
                'type': 'success',
            }
        }
    
    def action_print_idcard(self):
        """Print current employee's ID card (FRONT ONLY)"""
        self.ensure_one()
        self._save_wizard_data()
        self._save_current_employee_changes()
        
        # Use Square front report (main theme) - Simple call without extra data
        try:
            report = self.env.ref('jt_employee_icard.square_front_icard_report')
            return report.report_action(self.current_employee_id)
        except Exception as e:
            _logger.error("Error generating Square ID card: %s" % str(e))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Report Error',
                    'message': "Could not generate the Square ID card. Please check if the template is available.",
                    'sticky': False,
                    'type': 'warning',
                }
            }
    
    def action_print_all(self):
        """Print all selected employees' ID cards using Square theme (FRONT ONLY)"""
        self._save_wizard_data()
        self._save_current_employee_changes()
        
        # Use Square theme for all (main theme) - Simple call
        try:
            report = self.env.ref('jt_employee_icard.square_front_icard_report')
            return report.report_action(self.employee_ids)
        except Exception as e:
            _logger.error("Error generating Square ID cards: %s" % str(e))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Report Error',
                    'message': "Could not generate Square ID cards. Please check if the template is available.",
                    'sticky': False,
                    'type': 'warning',
                }
            }
    
    # REMOVED: action_print_back_side method - back card functionality completely removed
