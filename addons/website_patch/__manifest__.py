{
    'name': 'Website Column Error Fix',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Fixes errors in the website editor',
    'depends': ['website'],
    'assets': {
        'website.assets_editor': [
            'website_fix/static/src/js/column_fix.js',
        ],
    },
    'installable': True,
    'application': False,
}
