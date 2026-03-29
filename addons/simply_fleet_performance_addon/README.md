# Simply Fleet - Performance & Rewards Module

## Overview

This module extends Simply Fleet with a comprehensive **Driver Performance Tracking and Reward System**. It automatically tracks, analyzes, and rewards driver performance based on fuel efficiency, mileage, cost management, and driving consistency.

## Features

### 🎯 Automatic Performance Tracking
- Weekly performance reports (generated every Monday)
- Monthly performance reports (generated 1st of each month)
- Real-time calculation from fuel logs
- Complete historical tracking

### 📊 Multi-Metric Scoring (100 Points)
- **Fuel Efficiency (40 pts)**: Higher mileage = better score
- **Cost Management (30 pts)**: Lower cost per km = better score
- **Consistency (20 pts)**: Stable performance = better score
- **Activity Level (10 pts)**: More trips = better score

### 🏆 Performance Grades
| Grade | Score Range | Reward Points | Description |
|-------|-------------|---------------|-------------|
| Excellent | 90-100 | 100 + bonus | Outstanding performance |
| Good | 75-89 | 75 | Above average |
| Average | 60-74 | 50 | Satisfactory |
| Below Average | 40-59 | 25 | Needs improvement |
| Poor | 0-39 | 0 | Requires attention |

### 💰 Reward System
- Grade-based point allocation
- Bonus points for scores ≥ 95 (+20 points)
- Configurable conversion: ₹10 per point (weekly), ₹15 per point (monthly)
- Automatic reward calculation

### 📈 Visual Analytics
- Interactive performance dashboard
- Line charts for trend analysis
- Bar charts for driver comparison
- Pivot tables for detailed analysis
- Calendar view for period tracking
- Mobile-responsive design

### 🎛️ Management Tools
- Driver performance comparison
- Top performers ranking
- Performance approval workflow
- Reward processing tracking

## Installation

### Prerequisites
- Odoo 17.0
- Simply Fleet module installed
- HR module installed
- Active fuel logs with driver assignments

### Install Steps

1. **Copy module to addons directory:**
   ```bash
   cp -r simply_fleet_performance /path/to/odoo/addons/
   ```

2. **Restart Odoo server:**
   ```bash
   sudo systemctl restart odoo
   ```

3. **Update Apps List:**
   - Go to Apps menu
   - Click "Update Apps List"

4. **Install the module:**
   - Search for "Simply Fleet - Performance"
   - Click "Install"

## Configuration

### Initial Setup

1. **Verify Drivers:**
   - Go to HR → Employees
   - Ensure drivers have job titles containing "driver"
   - Verify they are marked as active

2. **Check Fuel Logs:**
   - Go to Simply Fleet → Fuel Logs
   - Ensure logs have driver assignments
   - Verify date, quantity, and distance fields are filled

3. **Configure Benchmarks (Optional):**
   - Edit `models/driver_performance.py`
   - Adjust benchmarks in `_compute_performance_score` function:
     ```python
     mileage_benchmark = 5.0  # km/L target
     cost_benchmark = 10.0    # ₹/km target
     ```

4. **Modify Rewards (Optional):**
   - Edit `models/driver_performance.py`
   - Adjust rewards in `_compute_reward_amount` function:
     ```python
     point_value = 10  # ₹ per point
     period_multiplier = 1.5  # for monthly
     ```

## Usage

### Menu Navigation
```
Simply Fleet
└── Performance
    ├── Dashboard          (Overview with charts)
    ├── Driver Performance (All performance records)
    ├── Top Performers     (Best drivers)
    └── Compare Drivers    (Comparison tool)
```

### Workflow

1. **Automatic Generation:**
   - System creates records via cron jobs
   - Weekly: Every Monday at 00:00
   - Monthly: 1st of month at 00:00

2. **Manual Creation:**
   - Go to Performance → Driver Performance
   - Click "New"
   - Select driver, period type, dates
   - Click "Calculate Performance"

3. **Review & Approve:**
   - Review calculated metrics
   - Click "Approve" if acceptable
   - Process payment/reward to driver
   - Click "Mark as Rewarded"

### Performance Dashboard

Access: **Simply Fleet → Performance → Dashboard**

Features:
- Total drivers count
- Average performance score
- Total rewards amount
- Excellent drivers count
- Top 10 performers list
- Performance trend charts
- Grade distribution

### Driver Comparison

Access: **Simply Fleet → Performance → Compare Drivers**

Steps:
1. Select period type (Weekly/Monthly)
2. Choose date range
3. Select specific drivers (optional)
4. Click "Generate Comparison"
5. View graphical comparison

## Performance Calculation

### Metrics Calculated
```python
total_trips = Count of fuel log entries
total_distance = Sum of all distances (km)
total_fuel = Sum of all fuel quantity (L)
average_mileage = total_distance / total_fuel
total_cost = Sum of all fuel costs (₹)
cost_per_km = total_cost / total_distance
best_mileage = Maximum mileage in period
worst_mileage = Minimum mileage in period
```

### Scoring Formula

**1. Mileage Score (40 points max)**
```
Score = min((actual_mileage / benchmark) × 40, 40)
Benchmark = 5.0 km/L (configurable)
```

**2. Cost Efficiency Score (30 points max)**
```
Score = min((benchmark / actual_cost_per_km) × 30, 30)
Benchmark = ₹10/km (configurable)
```

**3. Consistency Score (20 points max)**
```
variance = statistical_variance(all_mileages)
Score = max(20 - (variance / average × 10), 0)
```

**4. Activity Score (10 points max)**
```
Score = min((actual_trips / benchmark) × 10, 10)
Benchmark = 20 (weekly) or 80 (monthly)
```

**Total Performance Score** = Sum of all scores (max 100)

### Reward Calculation

**Point Allocation:**
```
Excellent (90-100):    100 points base + bonus
Good (75-89):          75 points
Average (60-74):       50 points
Below Average (40-59): 25 points
Poor (0-39):           0 points

Bonus: +20 points if score ≥ 95
```

**Monetary Conversion:**
```
Weekly:  Points × ₹10
Monthly: Points × ₹15 (1.5× multiplier)
```

**Example:**
```
Score: 92 (Good grade)
Base Points: 75
Weekly Reward: 75 × ₹10 = ₹750
Monthly Reward: 75 × ₹15 = ₹1,125
```

## Views

### Available Views
1. **Tree View** - Tabular list with sorting and filters
2. **Form View** - Detailed single record view
3. **Kanban View** - Card-based mobile-friendly view
4. **Graph View** - Line and bar charts
5. **Pivot View** - Interactive pivot tables
6. **Calendar View** - Timeline visualization

### Filters & Grouping

**Pre-built Filters:**
- This Week / This Month / Last Month
- By Period Type (Weekly/Monthly)
- By Grade (Excellent/Good/Average/Below/Poor)
- By Status (Draft/Calculated/Approved/Rewarded)

**Grouping Options:**
- By Driver
- By Period Type
- By Performance Grade
- By Status
- By Period Start Date

## Automated Jobs (Cron)

### Weekly Performance Generation
- **Frequency:** Every Monday at 00:00
- **Action:** Creates performance records for all active drivers
- **Period:** Previous Monday to Sunday

### Monthly Performance Generation
- **Frequency:** 1st day of month at 00:00
- **Action:** Creates performance records for all active drivers
- **Period:** Previous month (1st to last day)

### Managing Cron Jobs
- Go to: Settings → Technical → Scheduled Actions
- Search: "Driver Performance"
- Enable/Disable: Toggle "Active" field
- Test: Click "Run Manually"

## Security & Permissions

### Access Levels

| User Group | Read | Write | Create | Delete |
|------------|------|-------|--------|--------|
| Fleet User | ✓ | ✗ | ✗ | ✗ |
| Fleet Manager | ✓ | ✓ | ✓ | ✓ |

### Configuration
- Settings → Users & Companies → Users
- Select user → Groups tab
- Add "Simply Fleet / Manager" for full access

## Customization

### Adjust Benchmarks

File: `models/driver_performance.py`
Function: `_compute_performance_score` (around line 127)

```python
# Mileage benchmark (km/L)
mileage_benchmark = 5.0  # Change to your value

# Cost benchmark (₹/km)
cost_benchmark = 10.0  # Change to your value

# Trip benchmarks
trip_benchmark = 20 if weekly else 80  # Change values
```

### Modify Rewards

File: `models/driver_performance.py`
Function: `_compute_reward_amount` (around line 201)

```python
# Reward per point
point_value = 10  # Change to your value

# Monthly multiplier
period_multiplier = 1.5 if monthly else 1.0
```

### Change Scoring Weights

File: `models/driver_performance.py`
Function: `_compute_performance_score` (around line 115-145)

```python
# Current weights
mileage_weight = 40    # out of 100
cost_weight = 30       # out of 100
consistency_weight = 20 # out of 100
activity_weight = 10   # out of 100
```

## Troubleshooting

### Performance Not Calculating

**Issue:** Calculate button doesn't work

**Solution:**
- Verify fuel logs exist for the period
- Check driver is selected
- Ensure period dates are correct
- Review server logs for errors

### Cron Jobs Not Running

**Issue:** Automatic generation not working

**Solution:**
- Settings → Technical → Scheduled Actions
- Find "Generate Weekly/Monthly Driver Performance"
- Check "Active" = True
- Verify "Next Execution Date"
- Click "Run Manually" to test

### Missing Data

**Issue:** Metrics show 0 or blank

**Solution:**
- Verify fuel logs have all required fields
- Check odometer readings are correct
- Ensure distance is calculated
- Re-calculate performance

### Permission Errors

**Issue:** Access denied

**Solution:**
- Check user has "Simply Fleet Manager" group
- Verify security rules are installed
- Clear browser cache
- Re-login

## Technical Details

### Models

**simply.fleet.driver.performance**
- Main performance tracking model
- Stores all performance metrics
- Handles calculations and rewards

**simply.fleet.driver.performance.comparison**
- Transient model for comparison wizard
- Generates comparative reports

### Dependencies

```python
'depends': [
    'simply_fleet',  # Base fleet management
    'hr',           # Employee/driver data
    'mail',         # Chatter and notifications
]
```

### Database Tables

- `simply_fleet_driver_performance` - Main performance data
- `simply_fleet_driver_performance_comparison` - Temporary comparison data

## Support

### Documentation
- Full README: `/path/to/module/README.md`
- Installation Guide: See "Installation" section above
- In-app Help: Hover over field labels

### Bug Reports
- Check server logs: `/var/log/odoo/odoo.log`
- Enable debug mode: Append `?debug=1` to URL
- Review browser console for errors

### Contact
- Email: support@yourcompany.com
- Website: https://www.yourcompany.com

## Changelog

### Version 17.0.1.0.0 (2026-01-31)
- Initial release
- Automatic weekly and monthly performance tracking
- Multi-metric scoring system
- Reward points and monetary calculation
- Interactive dashboard with charts
- Driver comparison tools
- Top performers ranking
- Mobile-responsive design

## License

LGPL-3

## Credits

**Developed for:** Simply Fleet Management System
**Odoo Version:** 17.0
**Module Version:** 17.0.1.0.0

---

**Happy Fleet Management! 🚗📊🏆**
