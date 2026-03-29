# -*- coding: utf-8 -*-
{
    'name': 'Camera Provisioning (BLE WiFi Setup)',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'summary': 'Setup CCTV cameras via Bluetooth WiFi provisioning - like COFE app',
    'description': """
        Camera Provisioning Module for Odoo 17
        ======================================
        
        This module allows you to:
        - Scan for BLE cameras (XiongMai/COFE cameras)
        - Send WiFi credentials via Bluetooth
        - Register cameras in Odoo
        - View RTSP streams from registered cameras
        
        Works with:
        - COFE PTZ Ball Cameras
        - XiongMai (XM) based cameras
        - Any camera with BLE WiFi provisioning (Service UUID: 0x1910)
        
        Requires:
        - Modern browser with Web Bluetooth API support (Chrome, Edge, Opera)
        - HTTPS connection (required for Web Bluetooth)
        
        Developed for Annapurna Travels
    """,
    'author': 'Annapurna Travels',
    'website': 'https://annapurnatravels.co.in',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/camera_views.xml',
        'views/camera_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'camera_provisioning/static/src/js/ble_camera.js',
            'camera_provisioning/static/src/js/camera_widget.js',
            'camera_provisioning/static/src/css/camera.css',
            'camera_provisioning/static/src/xml/camera_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
