# -*- coding: utf-8 -*-
{
    'name': 'ZKTeco iClock Attendance Integration',
    'version': '17.0.2.1.0',
    'category': 'Human Resources',
    'summary': 'Integrate ZKTeco WL20/iClock devices with Odoo HR Attendance - Enhanced with FILO, Anti-Passback & Grace Rules',
    'description': """
        ZKTeco iClock Protocol Integration - Enhanced Version
        ======================================================
        
        Complete integration with ZKTeco biometric devices using iClock protocol.
        
        ✅ CORE FEATURES:
        -----------------
        * Real-time attendance sync from device to Odoo
        * Automatic check-in/check-out tracking
        * Multi-device support (unlimited devices)
        * Employee management with device linking
        * Push employees to device
        * Delete employees from device
        * Device status monitoring
        * Attendance reports and analytics
        
        ⭐ NEW ENHANCED RULES:
        ---------------------
        * 🎯 FILO Rule (First-In Last-Out): 
          - First punch of the day = Check-In
          - Last punch of the day = Check-Out
          - Intermediate punches ignored (configurable)
        
        * 🛡️ Anti-Passback / Duplicate Prevention:
          - Ignores duplicate punches within 2 minutes
          - Prevents accidental double-taps
          - Configurable time window
        
        * ⏰ Grace Period & Rounding:
          - Grace period support (default 15 minutes)
          - Time rounding to nearest interval (default 15 minutes)
          - Helps with payroll and shift management
        
        ✅ PROTOCOLS SUPPORTED:
        -----------------------
        * iClock Push Protocol (device pushes to server)
        * Works with WL20, K40, iClock series, and most ZKTeco devices
        
        ✅ NETWORK SETUP:
        -----------------
        * Device and Odoo can be on different networks
        * Works with cloud-hosted Odoo
        * No static IP required on device side
        * Compatible with Cloudflare Tunnel, ngrok, etc.
        
        ✅ HOW IT WORKS:
        ----------------
        1. Device pushes attendance to /iclock/cdata
        2. Module applies FILO + Anti-Passback rules
        3. Timestamps rounded based on configuration
        4. Attendance records created with check-in/check-out
        5. Employees matched by device_user_id
        6. Real-time dashboard updates
        
        ✅ CONFIGURATION:
        -----------------
        Edit controllers/main.py to configure:
        - DUPLICATE_PREVENTION_MINUTES = 2 (anti-passback window)
        - GRACE_PERIOD_MINUTES = 15 (grace period)
        - ROUNDING_MINUTES = 15 (time rounding, 0 to disable)
        - ENABLE_FILO_RULE = True (toggle FILO vs status-based)
        
        Device Setup:
        1. Install module
        2. Create device with Serial Number
        3. Add employees with Device User ID
        4. Configure device: Server = your-odoo-url.com, Port = 80/443
        5. Attendance data flows automatically!
        
        Version: 2.1.0 (Enhanced with FILO + Anti-Passback + Grace Rules)
        
        ✅ RECENT UPDATES:
        v2.1.0 - Added FILO, Anti-Passback, Grace Period & Rounding rules
        v2.0.2 - Fixed timezone handling (device local time → UTC → user timezone)
        v2.0.1 - Fixed menu navigation issue (removed tracking parameter)
        v2.0.0 - Initial release with full features
    """,
    'author': 'Custom Development',
    'website': '',
    'depends': ['hr', 'hr_attendance', 'web'],
    'external_dependencies': {
        'python': ['requests', 'pytz'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/zk_device_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_attendance_views.xml',
        'views/zk_dashboard_views.xml',
        'views/menu_views.xml',
        'data/ir_cron_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'zk_iclock_attendance/static/src/css/dashboard.css',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
