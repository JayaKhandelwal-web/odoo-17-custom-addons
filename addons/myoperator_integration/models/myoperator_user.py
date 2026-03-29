from odoo import models, fields, api


class MyOperatorUser(models.Model):
    _name = 'myoperator.user'
    _description = 'MyOperator User'
    _rec_name = 'name'

    config_id = fields.Many2one('myoperator.config', string='Configuration', required=True)
    user_id = fields.Char('MyOperator User ID', required=True, index=True)
    name = fields.Char('Name', required=True)
    email = fields.Char('Email')
    company_id_mo = fields.Char('MyOperator Company ID')
    uuid = fields.Char('UUID')
    
    # Link to Odoo user
    odoo_user_id = fields.Many2one('res.users', string='Odoo User',
                                  help='Link this MyOperator user to an Odoo user')
    
    # Status fields
    active = fields.Boolean('Active', default=True)
    synced_date = fields.Datetime('Last Synced', default=fields.Datetime.now)
    
    _sql_constraints = [
        ('unique_user_id_config', 'unique(user_id, config_id)', 
         'MyOperator User ID must be unique per configuration!')
    ]
    
    @api.model
    def find_user_by_email(self, email):
        """Find MyOperator user by email"""
        return self.search([('email', '=', email)], limit=1)
    
    def sync_with_odoo_user(self):
        """Try to automatically link with Odoo user based on email"""
        if self.email and not self.odoo_user_id:
            odoo_user = self.env['res.users'].search([('email', '=', self.email)], limit=1)
            if odoo_user:
                self.odoo_user_id = odoo_user.id