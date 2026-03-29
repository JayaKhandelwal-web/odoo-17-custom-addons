{
    'name': 'Employee ID Card',
    'summary': 'Print Standard ID Card for your employee from system',
    'version': '17.0.1.0.1',
    'category': 'Human Resources',
    'author': 'Jupical Technologies Pvt. Ltd.',
    'maintainer': 'Jupical Technologies Pvt. Ltd.',
    'contributors': ['Anil Kesariya <anil.r.kesariya@gmail.com>'],
    'website': 'https://www.jupical.com',
    'depends': ['hr'],
    'data': [
        # Security
        'security/employee_icard_security.xml',
        'security/ir.model.access.csv',
        
        # Views - Load wizard view FIRST
        'views/print_idcard_view.xml',  # Load this FIRST (contains the action)
        'views/employee.xml',           # Load this SECOND (references the action)
        
        # Reports - Square Theme Only
        'reports/square_id_front.xml',  # Square front side ONLY
    ],
    # FIXED HOOKS: Using correct Odoo 17 hook signatures
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'images': ['static/description/poster_image.gif'],
    'price': 5.00,
    'currency': 'USD'
}
