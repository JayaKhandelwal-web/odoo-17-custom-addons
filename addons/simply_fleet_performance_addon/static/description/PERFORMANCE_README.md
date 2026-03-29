# Driver Performance & Reward System

## Overview
The Driver Performance & Reward System is an advanced module for Simply Fleet that tracks, analyzes, and rewards driver performance based on multiple metrics including fuel efficiency, mileage, cost management, and consistency.

## Features

### 1. Performance Tracking
- **Weekly Performance Monitoring**: Track driver performance on a weekly basis
- **Monthly Performance Reports**: Comprehensive monthly performance analytics
- **Automatic Calculation**: Performance metrics are calculated automatically from fuel logs
- **Multi-metric Analysis**: Evaluates performance across 4 key areas:
  - Fuel Efficiency (40 points)
  - Cost Management (30 points)
  - Consistency (20 points)
  - Activity Level (10 points)

### 2. Performance Scoring System
The system uses a 100-point scale to evaluate driver performance:

| Score Range | Grade | Description |
|------------|-------|-------------|
| 90-100 | Excellent | Outstanding performance |
| 75-89 | Good | Above average performance |
| 60-74 | Average | Satisfactory performance |
| 40-59 | Below Average | Needs improvement |
| 0-39 | Poor | Significant improvement required |

### 3. Reward Points System
- **Grade-Based Points**:
  - Excellent: 100 points base
  - Good: 75 points base
  - Average: 50 points base
  - Below Average: 25 points base
  - Poor: 0 points

- **Bonus Points**:
  - +20 points for scores ≥ 95

- **Conversion to Currency**:
  - ₹10 per point for weekly performance
  - ₹15 per point for monthly performance (1.5x multiplier)

### 4. Visual Analytics
- **Performance Dashboard**: Overview of all drivers' performance
- **Line Charts**: Track performance trends over time
- **Column Charts**: Compare drivers side-by-side
- **Pie Charts**: Performance grade distribution
- **Calendar View**: See performance periods at a glance

### 5. Ranking System
- Automatic ranking of drivers within each period
- Top performers highlighted
- Comparative analysis tools

## Installation

### 1. Add the Performance Module Files

Copy the following files to your Simply Fleet module:

```bash
# Model
models/driver_performance.py

# Views
views/driver_performance_views.xml

# Data Files
data/performance_sequence.xml
data/performance_cron.xml

# Security
security/performance_security.csv

# Assets (JavaScript & CSS)
static/src/js/performance_dashboard.js
static/src/css/performance_dashboard.css
```

### 2. Update Module Files

**Update `models/__init__.py`:**
```python
from . import driver_performance  # Add this line
```

**Update `__manifest__.py`:**
Add the following to the 'data' section:
```python
'security/performance_security.csv',
'data/performance_sequence.xml',
'data/performance_cron.xml',
'views/driver_performance_views.xml',
```

Add to the 'assets' section:
```python
'assets': {
    'web.assets_backend': [
        # ... existing assets ...
        '/simply_fleet/static/src/css/performance_dashboard.css',
        '/simply_fleet/static/src/js/performance_dashboard.js',
    ],
}
```

### 3. Upgrade the Module

```bash
# Restart Odoo server
sudo systemctl restart odoo

# Or if using command line
./odoo-bin -u simply_fleet -d your_database
```

## Usage Guide

### Accessing the Performance Module

1. Navigate to **Simply Fleet** → **Performance** in the main menu
2. You'll see the following sub-menus:
   - **Dashboard**: Overview of all performance metrics
   - **Driver Performance**: List of all performance records
   - **Top Performers**: Quick access to best performing drivers
   - **Compare Drivers**: Tool for comparing multiple drivers

### Automatic Performance Generation

The system automatically generates performance records:
- **Weekly**: Every Monday at 00:00
- **Monthly**: First day of each month at 00:00

### Manual Performance Generation

To manually create a performance record:

1. Go to **Performance** → **Driver Performance**
2. Click **New**
3. Fill in the form:
   - **Driver**: Select the driver
   - **Period Type**: Choose Weekly or Monthly
   - **Period Start**: Start date of the period
   - **Period End**: End date of the period
4. Click **Calculate Performance** button
5. Review the calculated metrics
6. Click **Approve** to finalize
7. Click **Mark as Rewarded** when rewards are processed

### Understanding Performance Metrics

#### 1. Performance Score Components

**Mileage Score (40 points max)**
- Benchmark: 5 km/L for buses
- Formula: `(Actual Mileage / Benchmark) × 40`
- Higher mileage = Better score

**Cost Efficiency Score (30 points max)**
- Benchmark: ₹10 per km
- Formula: `(Benchmark / Actual Cost per KM) × 30`
- Lower cost per km = Better score

**Consistency Score (20 points max)**
- Based on variance in mileage across trips
- Formula: `20 - (Variance/Average × 10)`
- More consistent performance = Better score

**Activity Score (10 points max)**
- Weekly benchmark: 20 trips
- Monthly benchmark: 80 trips
- Formula: `(Actual Trips / Benchmark) × 10`

#### 2. Key Metrics Displayed

- **Total Trips**: Number of fuel logs in the period
- **Total Distance**: Sum of all distances traveled
- **Total Fuel Consumed**: Total liters of fuel used
- **Average Mileage**: Overall km/L efficiency
- **Best/Worst Mileage**: Highest and lowest mileage in period
- **Total Fuel Cost**: Total amount spent on fuel
- **Cost per KM**: Average cost per kilometer
- **Rank**: Position among all drivers in the period

### Using the Dashboard

1. **Filter by Period**:
   - Click "Weekly" or "Monthly" buttons
   - Use date filters for custom ranges

2. **View Statistics**:
   - Total Drivers: Number of active drivers
   - Average Score: Mean performance score
   - Total Rewards: Sum of all reward amounts
   - Excellent Drivers: Count of top performers

3. **Top Performers List**:
   - Ranked 1-10 drivers
   - Color-coded badges for rank
   - Click any card to view full details

4. **Performance Charts**:
   - Line charts show trends over time
   - Bar charts compare drivers
   - Pivot tables for detailed analysis

### Comparing Drivers

1. Go to **Performance** → **Compare Drivers**
2. Select:
   - Period Type (Weekly/Monthly)
   - Date From and Date To
   - Specific drivers (optional - leave empty for all)
3. Click **Generate Comparison**
4. View the graphical comparison

### Approving and Processing Rewards

**Workflow:**
```
Draft → Calculate → Approve → Mark as Rewarded
```

**Steps:**
1. System generates performance records automatically
2. Manager reviews and clicks "Calculate Performance"
3. Review all metrics and scores
4. Click "Approve" if acceptable
5. Process payment/reward to driver
6. Click "Mark as Rewarded" to complete

### Viewing Driver History

To see a driver's performance history:

1. Go to **HR** → **Employees**
2. Open the driver's record
3. Click the **Performance** smart button (if available)
4. Or filter performance records by driver name

## Customization Options

### Adjusting Benchmarks

Edit `driver_performance.py`, function `_compute_performance_score`:

```python
# Change mileage benchmark (default 5.0 km/L)
mileage_benchmark = 6.0  # Your value

# Change cost benchmark (default ₹10 per km)
cost_benchmark = 12.0  # Your value

# Change trip benchmarks
trip_benchmark = 25 if record.period_type == 'weekly' else 100
```

### Modifying Reward Amounts

Edit `driver_performance.py`, function `_compute_reward_amount`:

```python
# Change point value (default ₹10 per point)
point_value = 15  # Your value

# Change period multiplier (default 1.5x for monthly)
period_multiplier = 2.0 if record.period_type == 'monthly' else 1.0
```

### Changing Cron Schedule

Edit `data/performance_cron.xml`:

```xml
<!-- For weekly - change day/time -->
<field name="interval_number">1</field>
<field name="interval_type">weeks</field>

<!-- For monthly - change day/time -->
<field name="interval_number">1</field>
<field name="interval_type">months</field>
```

## Reports & Analytics

### Available Views

1. **Tree View**: Tabular list of all records
2. **Form View**: Detailed single record view
3. **Kanban View**: Card-based mobile-friendly view
4. **Graph View**: Line and bar charts
5. **Pivot View**: Interactive pivot tables
6. **Calendar View**: Timeline visualization

### Grouping Options

Group performance data by:
- Driver
- Period Type
- Performance Grade
- Status
- Period Start Date

### Filters

Pre-built filters:
- This Week
- This Month
- Last Month
- By Grade (Excellent, Good, Average, etc.)
- By Status (Draft, Calculated, Approved, Rewarded)

## Best Practices

### For Managers

1. **Review Weekly**: Check performance records every Monday
2. **Monthly Reviews**: Conduct detailed reviews at month-end
3. **Quick Approval**: Approve good performers promptly
4. **Investigation**: Review poor performers individually
5. **Communication**: Share performance metrics with drivers

### For System Administrators

1. **Regular Backups**: Backup performance data regularly
2. **Monitor Crons**: Ensure cron jobs are running
3. **Audit Trails**: Use chatter for all approvals
4. **Data Cleanup**: Archive old records periodically
5. **Performance Tuning**: Monitor query performance for large datasets

### For Drivers

1. **Check Dashboard**: Review your performance regularly
2. **Fuel Efficiency**: Focus on maintaining consistent mileage
3. **Cost Control**: Be mindful of fuel costs
4. **Regular Updates**: Ensure fuel logs are up to date
5. **Ask Questions**: Clarify scoring criteria with managers

## Troubleshooting

### Performance Not Calculating

**Issue**: Calculate button doesn't work
**Solution**: 
- Ensure fuel logs exist for the period
- Check that driver is selected
- Verify period dates are correct

### Cron Jobs Not Running

**Issue**: Automatic generation not working
**Solution**:
- Go to Settings → Technical → Scheduled Actions
- Find "Generate Weekly/Monthly Driver Performance"
- Check if Active = True
- Check Next Execution Date
- Manually trigger with "Run Manually" button

### Missing Data in Reports

**Issue**: Some metrics show 0 or are blank
**Solution**:
- Verify fuel logs have all required fields
- Check odometer readings are correct
- Ensure distance is calculated properly
- Re-calculate performance

### Permission Issues

**Issue**: Users can't access performance module
**Solution**:
- Check user groups (Settings → Users)
- Ensure user has "Simply Fleet Manager" role
- Verify security rules in `performance_security.csv`

## API Integration

### Creating Performance Record via Code

```python
# Get the model
Performance = env['simply.fleet.driver.performance']

# Create record
perf = Performance.create({
    'driver_id': driver.id,
    'period_type': 'weekly',
    'period_start': '2026-01-27',
    'period_end': '2026-02-02',
})

# Calculate performance
perf.action_calculate_performance()

# Approve
perf.action_approve()
```

### Querying Performance Data

```python
# Get top 10 performers this month
performances = env['simply.fleet.driver.performance'].search([
    ('period_type', '=', 'monthly'),
    ('period_start', '>=', '2026-01-01'),
    ('period_end', '<=', '2026-01-31'),
], order='performance_score desc', limit=10)

# Get specific driver's performance
driver_perfs = env['simply.fleet.driver.performance'].search([
    ('driver_id', '=', driver_id),
], order='period_start desc')
```

## Support & Maintenance

### Version Information
- Module Version: 17.0.1.0.3
- Odoo Version: 17.0
- Last Updated: January 2026

### Change Log

**v17.0.1.0.3 (January 2026)**
- Added Driver Performance & Reward System
- Automatic weekly and monthly performance calculation
- Visual performance dashboard
- Driver comparison tools
- Reward points and monetary calculation

### Contributing

For bugs, feature requests, or contributions:
1. Document the issue/feature clearly
2. Provide sample data if reporting a bug
3. Test thoroughly before submitting changes
4. Follow Odoo coding standards

## License

This module is licensed under LGPL-3.

---

**Need Help?**
- Check the documentation above
- Review Odoo community forums
- Contact your system administrator
- Reach out to module developers

**Happy Tracking! 🚗📊🏆**
