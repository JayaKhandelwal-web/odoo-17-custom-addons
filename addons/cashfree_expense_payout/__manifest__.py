# -*- coding: utf-8 -*-
{
    'name': 'Cashfree Expense Payout - Annapurna Travels',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Auto-disburse employee expense reimbursements via Cashfree Payouts V2',
    'description': """
        Integrates Cashfree Payouts V2 API with Odoo HR Expenses.
        - Adds 'Pay via Cashfree' button on validated expense sheets
        - Uses employee's saved bank account (bank_account_id on hr.employee)
        - Auto-creates beneficiary on Cashfree if not already registered
        - Tracks transfer status via webhook or manual refresh
        - Logs all activity in expense sheet chatter
    """,
    'author': 'AlignTogether Solutions',
    'website': 'https://www.aligntogether.in',
    'depends': ['hr_expense', 'mail'],
    'data': [
        'security/cashfree_security.xml',
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',
        'views/res_config_settings_views.xml',
        'views/hr_expense_sheet_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
