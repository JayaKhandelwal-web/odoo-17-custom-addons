"""
Fixed module hooks for Employee ID Card - Odoo 17 Compatible
Handles automatic Employee ID generation on installation
"""

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """
    Fixed post-installation hook for Odoo 17
    Automatically generates Employee IDs for existing employees
    """
    _logger.info("=== Employee ID Card Post-Installation Hook (Fixed) ===")
    
    try:
        # Check if sequence exists, create if not
        sequence = env['ir.sequence'].search([('code', '=', 'seqemp.seqemp')], limit=1)
        if not sequence:
            _logger.info("Creating Employee ID sequence...")
            env['ir.sequence'].create({
                'name': 'Employee Sequence',
                'code': 'seqemp.seqemp',
                'prefix': 'EMP',
                'padding': 5,
                'implementation': 'no_gap',
            })
            _logger.info("Employee ID sequence created successfully")
        
        # Automatically generate Employee IDs for existing employees
        _logger.info("Starting automatic Employee ID generation...")
        
        # Find employees without proper IDs
        employees_needing_id = env['hr.employee'].search([
            '|', '|',
            ('emp_id', '=', False),
            ('emp_id', '=', 'New'),
            ('emp_id', '=', '')
        ])
        
        if employees_needing_id:
            _logger.info(f"Found {len(employees_needing_id)} employees needing Employee IDs")
            
            success_count = 0
            for employee in employees_needing_id:
                try:
                    # Use the employee model's own generation method
                    new_id = employee._generate_employee_id()
                    employee.sudo().write({'emp_id': new_id})
                    success_count += 1
                    _logger.info(f"Generated Employee ID {new_id} for {employee.name}")
                except Exception as e:
                    _logger.error(f"Failed to generate ID for {employee.name}: {str(e)}")
            
            _logger.info(f"Employee ID generation completed. Success: {success_count}/{len(employees_needing_id)}")
        else:
            _logger.info("No employees need Employee ID generation")
        
        # Commit changes
        env.cr.commit()
        
        _logger.info("=== Employee ID Card Post-Installation Completed Successfully ===")
        
    except Exception as e:
        _logger.error(f"Post-installation hook failed: {str(e)}")
        env.cr.rollback()
        _logger.warning("Installation completed with warnings. Use manual buttons to generate Employee IDs.")

def uninstall_hook(env):
    """
    Fixed pre-uninstall hook for Odoo 17
    """
    _logger.info("=== Employee ID Card Module Uninstalling ===")
    try:
        # Optional: Clean up sequence if needed
        # sequence = env['ir.sequence'].search([('code', '=', 'seqemp.seqemp')])
        # if sequence:
        #     sequence.unlink()
        #     _logger.info("Employee ID sequence removed")
        pass
    except Exception as e:
        _logger.warning(f"Uninstall hook warning: {str(e)}")
    
    _logger.info("Employee ID Card module uninstalled successfully")
