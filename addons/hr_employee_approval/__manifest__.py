{
    'name': 'HR Employee Approval Workflow',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Send approval email to manager when employee is created',
    'description': """
        When a new employee is created:
        - Employee is saved as 'Pending Approval' (inactive)
        - Email is automatically sent to the Manager
        - Manager can Approve or Reject from Odoo
        - On Approval, Employee becomes active in the system
    """,
    'author': 'Annapurna Tour & Travels',
    'depends': ['hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/email_template.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
