# Simply Fleet Performance Module - Directory Structure

```
simply_fleet_performance/
│
├── __init__.py                     # Main module initialization
├── __manifest__.py                 # Module manifest with dependencies and metadata
├── README.md                       # Main documentation
├── CHANGELOG.md                    # Version history and changes
│
├── models/                         # Python models
│   ├── __init__.py                # Models initialization
│   └── driver_performance.py      # Main performance tracking model (569 lines)
│
├── views/                          # XML views and UI definitions
│   └── driver_performance_views.xml  # All views, menus, and actions (521 lines)
│
├── data/                           # Data files
│   ├── performance_sequence.xml   # Sequence for PERF/00001 numbering
│   └── performance_cron.xml       # Automated cron jobs for weekly/monthly
│
├── security/                       # Access control
│   └── ir.model.access.csv        # User and manager permissions
│
└── static/                         # Static assets
    ├── description/                # Module description and docs
    │   ├── icon.png.txt           # Placeholder for module icon
    │   ├── INSTALLATION_GUIDE.md  # Installation instructions
    │   ├── MODULE_SUMMARY.md      # Technical summary
    │   └── PERFORMANCE_README.md  # Complete feature documentation
    │
    └── src/                        # Source files for web
        ├── css/
        │   └── performance_dashboard.css  # Dashboard styling (285 lines)
        └── js/
            └── performance_dashboard.js   # Dashboard JavaScript (110 lines)
```

## File Descriptions

### Root Files

**__init__.py**
- Main module entry point
- Imports models package

**__manifest__.py** 
- Module metadata and configuration
- Dependencies: simply_fleet, hr, mail
- Data file declarations
- Asset declarations
- Version: 17.0.1.0.0

**README.md**
- Complete module documentation
- Installation guide
- Usage instructions
- Configuration options
- Troubleshooting guide

**CHANGELOG.md**
- Version history
- Feature additions
- Bug fixes
- Future plans

### Models (models/)

**driver_performance.py**
- Main model: `simply.fleet.driver.performance`
- Wizard model: `simply.fleet.driver.performance.comparison`
- Fuel log extension: Adds performance_id field
- Functions:
  - Performance calculation
  - Reward computation
  - Ranking system
  - Automatic generation (weekly/monthly)

### Views (views/)

**driver_performance_views.xml**
- Tree view (tabular list)
- Form view (detailed record)
- Kanban view (mobile cards)
- Graph view (charts)
- Pivot view (analysis)
- Calendar view (timeline)
- Search view (filters)
- Menu structure
- Actions
- Comparison wizard

### Data (data/)

**performance_sequence.xml**
- Sequence generator
- Format: PERF/00001
- Auto-increment

**performance_cron.xml**
- Weekly cron (every Monday 00:00)
- Monthly cron (1st of month 00:00)
- Automatic performance generation

### Security (security/)

**ir.model.access.csv**
- User permissions (read only)
- Manager permissions (full access)
- Model access rules

### Static Assets (static/)

**description/**
- Documentation files
- Module description
- Icon placeholder

**src/css/**
- Dashboard styling
- Responsive design
- Color schemes
- Animations

**src/js/**
- Dashboard component
- Data loading
- Chart rendering
- Interactive features

## Key Features by File

### driver_performance.py
✓ Automatic performance calculation
✓ Multi-metric scoring (100 points)
✓ Reward point system
✓ Grade calculation
✓ Ranking algorithm
✓ Weekly/monthly generation
✓ Comparison tools

### driver_performance_views.xml
✓ 6 different view types
✓ Performance dashboard
✓ Top performers list
✓ Driver comparison wizard
✓ Interactive filters
✓ Smart grouping
✓ Mobile-responsive

### performance_dashboard.css
✓ Modern design
✓ Color-coded grades
✓ Responsive layout
✓ Animated elements
✓ Card-based UI
✓ Mobile optimization

### performance_dashboard.js
✓ Real-time data loading
✓ Chart integration
✓ Filter functionality
✓ Interactive statistics
✓ Action handlers

## Installation Location

Copy entire `simply_fleet_performance/` folder to:
```
/path/to/odoo/addons/simply_fleet_performance/
```

Or for custom addons:
```
/path/to/custom_addons/simply_fleet_performance/
```

Then:
1. Restart Odoo
2. Update Apps List
3. Search "Simply Fleet - Performance"
4. Click Install

## Dependencies

The module depends on:
- `simply_fleet` - Base fleet management module
- `hr` - Human Resources for driver data
- `mail` - For chatter and notifications

## File Sizes

```
Total Module Size:  ~150 KB
Python Code:        ~65 KB
XML Views:          ~45 KB
JavaScript:         ~8 KB
CSS:                ~12 KB
Documentation:      ~20 KB
```

## Lines of Code

```
Python:         ~600 lines
XML:            ~520 lines
JavaScript:     ~110 lines
CSS:            ~285 lines
Documentation:  ~1,030 lines
Total:          ~2,545 lines
```

## Compatibility

- Odoo Version: 17.0
- Database: PostgreSQL
- Python: 3.8+
- Browsers: Chrome, Firefox, Safari, Edge (latest versions)
- Mobile: iOS Safari, Android Chrome

## License

LGPL-3

---

For installation instructions, see INSTALLATION_GUIDE.md
For feature documentation, see PERFORMANCE_README.md
For technical details, see MODULE_SUMMARY.md
