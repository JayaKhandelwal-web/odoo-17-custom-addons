# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import UserError


class BaseModelExtend(models.AbstractModel):
    """
    Extended base model to add custom button actions for all models
    """
    _inherit = 'base'

    def action_custom_save(self):
        """
        Custom Save action - saves the current record
        """
        self.ensure_one()
        
        # If it's a new record, save it
        if not self.id or self._origin.id is False:
            # For new records, the save happens automatically when form is submitted
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Record created successfully!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        
        # For existing records, save any changes
        try:
            # The record is already saved by Odoo's form view mechanism
            # We just show a notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Record saved successfully!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(f"Failed to save record: {str(e)}")

    def action_custom_delete(self):
        """
        Custom Delete action - deletes the current record with confirmation
        """
        self.ensure_one()
        
        try:
            # Store the model info before deletion
            model_name = self._description or self._name
            
            # Delete the record
            self.unlink()
            
            # Return to the list view with success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Deleted',
                    'message': f'{model_name} deleted successfully!',
                    'type': 'success',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    }
                }
            }
        except Exception as e:
            raise UserError(f"Failed to delete record: {str(e)}")

    def action_custom_back(self):
        """
        Custom Back action - closes the current form view
        """
        return {
            'type': 'ir.actions.act_window_close'
        }
