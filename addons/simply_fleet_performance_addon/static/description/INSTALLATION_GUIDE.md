# Quick Installation Guide - Driver Performance Module

## File Structure

Place the created files in your Simply Fleet module directory as follows:

```
simply_fleet/
│
├── models/
│   ├── __init__.py                      (UPDATE - add: from . import driver_performance)
│   └── driver_performance.py            (NEW FILE - main performance model)
│
├── views/
│   └── driver_performance_views.xml     (NEW FILE - all views and menus)
│
├── data/
│   ├── performance_sequence.xml         (NEW FILE - sequence for performance records)
│   └── performance_cron.xml             (NEW FILE - automated cron jobs)
│
├── security/
│   └── performance_security.csv         (NEW FILE - access rights)
│
├── static/
│   ├── src/
│   │   ├── js/
│   │   │   └── performance_dashboard.js (NEW FILE - dashboard JavaScript)
│   │   └── css/
│   │       └── performance_dashboard.css(NEW FILE - dashboard styles)
│
└── __manifest__.py                      (UPDATE - add new data files and assets)
```

## Step-by-Step Installation

### Step 1: Copy Files to Module

1. **Copy Model File**
   ```bash
   cp driver_performance.py /path/to/addons/simply_fleet/models/
   ```

2. **Copy View File**
   ```bash
   cp driver_performance_views.xml /path/to/addons/simply_fleet/views/
   ```

3. **Copy Data Files**
   ```bash
   cp performance_sequence.xml /path/to/addons/simply_fleet/data/
   cp performance_cron.xml /path/to/addons/simply_fleet/data/
   ```

4. **Copy Security File**
   ```bash
   cp performance_security.csv /path/to/addons/simply_fleet/security/
   ```

5. **Copy Assets**
   ```bash
   # Create directories if they don't exist
   mkdir -p /path/to/addons/simply_fleet/static/src/js
   mkdir -p /path/to/addons/simply_fleet/static/src/css
   
   # Copy files
   cp performance_dashboard.js /path/to/addons/simply_fleet/static/src/js/
   cp performance_dashboard.css /path/to/addons/simply_fleet/static/src/css/
   ```

### Step 2: Update Module Files

#### A. Update models/__init__.py

Open `/path/to/addons/simply_fleet/models/__init__.py` and add this line at the end:

```python
from . import driver_performance  # Add this line
```

Your complete file should look like:
```python
from . import vehicle
from . import document
from . import fuel_log
from . import transaction_type
from . import hr_extend
from . import fleet_manager_assignment
from . import battery
from . import tyre
from . import vehicle_image
from . import simply_fleet_camera
from . import vehicle_asset
from . import inspection
from . import work_order
from . import barcode_wizard
from . import driver_performance  # NEW LINE
```

#### B. Update __manifest__.py

1. **Update version number** (line 3):
   ```python
   'version': '17.0.1.0.3',  # Change from 17.0.1.0.2 to 17.0.1.0.3
   ```

2. **Update description** (add to features list around line 10):
   ```python
   - Driver Performance & Rewards System (NEW)
       * Weekly and Monthly Performance Tracking
       * Performance Score Calculation
       * Automatic Reward Points System
       * Performance Analytics Dashboard
       * Driver Comparison Tools
   ```

3. **Update 'data' section** (add these lines in the appropriate places):
   ```python
   'data': [
       # Security
       'security/simply_fleet_security.xml',
       'security/ir.model.access.csv',
       'security/performance_security.csv',  # ADD THIS LINE
       
       # Data
       'data/simply_fleet_sequence.xml',
       'data/mail_template_data.xml',
       'data/document_cron.xml',
       'data/battery_sequence.xml',
       'data/work_order_sequence.xml',
       'data/performance_sequence.xml',  # ADD THIS LINE
       'data/performance_cron.xml',      # ADD THIS LINE
       
       # ... (rest of your data files) ...
       
       'views/simply_fleet_work_order_views.xml',
       'views/barcode_wizard_views.xml',
       'views/driver_performance_views.xml',  # ADD THIS LINE
   ],
   ```

4. **Update 'assets' section** (add these lines):
   ```python
   'assets': {
       'web.assets_backend': [
           '/simply_fleet/static/src/css/mobile_styles.css',
           '/simply_fleet/static/src/js/barcode_handler.js',
           '/simply_fleet/static/src/css/vehicle_kanban.css',
           '/simply_fleet/static/src/css/inspection_kanban.css',
           '/simply_fleet/static/src/css/performance_dashboard.css',  # ADD THIS LINE
           '/simply_fleet/static/src/js/performance_dashboard.js',    # ADD THIS LINE
       ],
   },
   ```

### Step 3: Upgrade the Module

#### Option A: Using Odoo Web Interface

1. Go to **Apps** menu
2. Remove **Apps** filter from search bar
3. Search for **Simply Fleet**
4. Click **Upgrade** button

#### Option B: Using Command Line

1. **Restart Odoo Server:**
   ```bash
   # If using systemd
   sudo systemctl restart odoo
   
   # If using supervisor
   sudo supervisorctl restart odoo
   ```

2. **Upgrade Module via Command:**
   ```bash
   # Navigate to Odoo directory
   cd /path/to/odoo
   
   # Run upgrade command
   ./odoo-bin -u simply_fleet -d your_database_name --stop-after-init
   ```

3. **Or use the Odoo shell:**
   ```bash
   ./odoo-bin shell -d your_database_name
   
   # In the shell:
   >>> self.env['ir.module.module'].search([('name', '=', 'simply_fleet')]).button_immediate_upgrade()
   ```

### Step 4: Verify Installation

1. **Check Menu Items:**
   - Go to Simply Fleet
   - You should see a new **Performance** menu
   - Sub-menus: Dashboard, Driver Performance, Top Performers, Compare Drivers

2. **Check Model Installation:**
   - Go to Settings → Technical → Models
   - Search for "simply.fleet.driver.performance"
   - Should see the model listed

3. **Check Cron Jobs:**
   - Go to Settings → Technical → Scheduled Actions
   - Search for "Driver Performance"
   - Should see two cron jobs:
     - "Generate Weekly Driver Performance"
     - "Generate Monthly Driver Performance"

4. **Test Manual Creation:**
   - Go to Performance → Driver Performance
   - Click **New**
   - Fill in driver, period type, dates
   - Click **Calculate Performance**
   - Should see metrics populated

### Step 5: Initial Data Setup

1. **Ensure Drivers are Set Up:**
   - Go to HR → Employees
   - Ensure drivers have job titles containing "driver"
   - Verify they are marked as active

2. **Verify Fuel Logs:**
   - Go to Simply Fleet → Fuel Logs
   - Ensure existing fuel logs have:
     - Driver assigned
     - Date, quantity, distance filled in
     - Mileage calculated

3. **Generate First Performance Records:**
   - Go to Performance → Driver Performance
   - Click **New** for each driver
   - Set period type (weekly or monthly)
   - Set date range
   - Click **Calculate Performance**

## Troubleshooting

### Issue: Import Error

**Error:** `ImportError: cannot import name 'driver_performance'`

**Solution:**
1. Check that `driver_performance.py` is in the `models/` directory
2. Verify `models/__init__.py` has the import line
3. Restart Odoo server completely

### Issue: View Not Found

**Error:** `View not found: driver_performance_views`

**Solution:**
1. Check that `driver_performance_views.xml` is in the `views/` directory
2. Verify the file is listed in `__manifest__.py` under 'data'
3. Check for XML syntax errors in the file
4. Try upgrading module again

### Issue: Access Rights Error

**Error:** `Access rights error for model simply.fleet.driver.performance`

**Solution:**
1. Check that `performance_security.csv` is in `security/` directory
2. Verify it's listed in `__manifest__.py` under 'data'
3. Check user has "Simply Fleet Manager" group
4. Try: Settings → Users → Select user → Add "Simply Fleet Manager" group

### Issue: Cron Jobs Not Working

**Solution:**
1. Go to Settings → Technical → Scheduled Actions
2. Find performance cron jobs
3. Check "Active" is True
4. Check "Next Execution Date" is in the future
5. Click "Run Manually" to test
6. Check server logs for errors

### Issue: Menu Not Visible

**Solution:**
1. Refresh browser (Ctrl+F5)
2. Clear browser cache
3. Check user permissions
4. Verify menu items in `driver_performance_views.xml`

## Post-Installation Configuration

### 1. Adjust Performance Benchmarks

Edit `models/driver_performance.py`, function `_compute_performance_score`:

```python
# Around line 127-128
mileage_benchmark = 5.0  # Change to your fleet's average
cost_benchmark = 10.0    # Change to your cost target
```

### 2. Modify Reward Amounts

Edit `models/driver_performance.py`, function `_compute_reward_amount`:

```python
# Around line 201
point_value = 10  # ₹ per point
period_multiplier = 1.5 if record.period_type == 'monthly' else 1.0
```

### 3. Set Cron Schedule

Edit `data/performance_cron.xml`:

```xml
<!-- For weekly - line 11 -->
<field name="interval_number">1</field>
<field name="interval_type">weeks</field>

<!-- For monthly - line 22 -->
<field name="interval_number">1</field>
<field name="interval_type">months</field>
```

### 4. Initial Test Run

```bash
# SSH into server
ssh user@your-server

# Open Odoo shell
cd /path/to/odoo
./odoo-bin shell -d your_database

# Generate test performance
>>> Performance = env['simply.fleet.driver.performance']
>>> Performance.generate_weekly_performance()
>>> env.cr.commit()
>>> exit()
```

## Backup Before Installation

**IMPORTANT:** Always backup before upgrading!

```bash
# Backup database
pg_dump your_database_name > backup_before_performance_$(date +%Y%m%d).sql

# Backup filestore
cp -r /path/to/odoo/filestore/your_database_name /path/to/backup/filestore_$(date +%Y%m%d)

# Backup addons
cp -r /path/to/addons/simply_fleet /path/to/backup/simply_fleet_$(date +%Y%m%d)
```

## Testing Checklist

After installation, test:

- [ ] Menu "Performance" appears in Simply Fleet
- [ ] Can create new performance record
- [ ] "Calculate Performance" button works
- [ ] Metrics are populated correctly
- [ ] Can approve performance record
- [ ] Can mark as rewarded
- [ ] Dashboard shows statistics
- [ ] Charts render properly
- [ ] Filters work in search view
- [ ] Cron jobs are scheduled
- [ ] Security/permissions work correctly

## Next Steps

1. Read the full documentation: `PERFORMANCE_README.md`
2. Configure benchmarks for your fleet
3. Train managers on the approval workflow
4. Set up reporting schedules
5. Communicate system to drivers

## Support

If you encounter issues:

1. Check server logs: `/var/log/odoo/odoo.log`
2. Enable debug mode: Append `?debug=1` to URL
3. Check browser console for JavaScript errors
4. Review this guide's troubleshooting section
5. Contact your Odoo administrator

---

**Installation Complete! 🎉**

Access your new Performance module at:
**Simply Fleet → Performance**
