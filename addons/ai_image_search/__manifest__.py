{
    'name': 'AI Image Search',
    'version': '17.0.2.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'AI-powered multi-view image search for vehicle parts with similarity display',
    'depends': ['base', 'product', 'stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/image_search_wizard_views.xml',
    ],
    'external_dependencies': {
        'python': [
            'numpy',
            'opencv-python-headless', 
            'scikit-learn',
            'Pillow'
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}