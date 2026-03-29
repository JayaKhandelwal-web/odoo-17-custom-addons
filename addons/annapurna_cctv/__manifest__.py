{
    'name': 'Annapurna CCTV Manager',
    'version': '17.0.1.0.0',
    'category': 'Security',
    'summary': 'CCTV Camera Management with ONVIF, Live Stream, PTZ & Snapshots',
    'description': """
        Full CCTV Camera Integration for Odoo 17
        =========================================
        - Add and manage ONVIF-compatible cameras
        - Live RTSP stream viewer (via HLS / MediaMTX)
        - PTZ Pan/Tilt/Zoom controls via ONVIF
        - Snapshot capture and storage per camera
        - Camera online/offline status with auto-ping
        - Multi-camera dashboard with grid view
        - Recordings and snapshots management
        - Auto status check every 5 minutes (cron)
    """,
    'author': 'Annapurna Travels',
    'website': 'https://annapurnatravels.co.in',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/cctv_data.xml',
        'views/cctv_camera_views.xml',
        'views/cctv_recording_views.xml',
        'views/cctv_dashboard_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'annapurna_cctv/static/src/css/cctv.css',
            'annapurna_cctv/static/src/js/cctv_stream_widget.js',
            'annapurna_cctv/static/src/js/cctv_dashboard.js',
            'annapurna_cctv/static/src/xml/cctv_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
