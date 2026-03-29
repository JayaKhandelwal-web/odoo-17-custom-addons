# Module Structure Documentation

## 📂 Complete Directory Structure

```
odoo_custom_buttons/
│
├── __init__.py                          # Module initialization
├── __manifest__.py                      # Module metadata and configuration
│
├── models/                              # Python models
│   ├── __init__.py                     # Models package init
│   └── base_model.py                   # Extended base model with button actions
│
├── static/                              # Static assets
│   └── src/
│       ├── css/
│       │   └── custom_buttons.css      # Button styles (GREEN, RED, YELLOW)
│       └── js/
│           └── form_buttons.js         # JavaScript functionality & shortcuts
│
├── views/                               # XML views and templates
│   ├── webclient_templates.xml         # Asset loading templates
│   └── form_view_examples.xml          # Example view inheritances
│
├── README.md                            # Complete documentation
├── INSTALLATION.md                      # Step-by-step installation guide
├── QUICK_REFERENCE.md                   # Quick tips and templates
└── MODULE_STRUCTURE.md                  # This file
```

---

## 📄 File Descriptions

### Root Files

#### `__init__.py`
```python
# Initializes the module
# Imports models package
from . import models
```

#### `__manifest__.py`
```python
# Module metadata:
# - Name, version, category
# - Dependencies (base, web)
# - Data files (XML views)
# - Assets (CSS, JS)
# - Installation settings
```

---

### Models Directory (`models/`)

#### `models/__init__.py`
```python
# Imports model files
from . import base_model
```

#### `models/base_model.py`
Contains three main methods added to all Odoo models:

1. **`action_custom_save()`**
   - Saves the current record
   - Shows success notification
   - Returns notification action

2. **`action_custom_delete()`**
   - Deletes the current record
   - Asks for confirmation (handled in XML)
   - Shows success message
   - Closes form and returns to list

3. **`action_custom_back()`**
   - Closes the current form
   - Returns to previous view
   - No data changes

**Inheritance**: Extends `models.AbstractModel` with `_inherit = 'base'`  
**Scope**: Available to ALL models in Odoo

---

### Static Assets (`static/src/`)

#### `static/src/css/custom_buttons.css`

**Purpose**: Define button appearance and behavior

**Main Classes**:
- `.o_form_custom_buttons_container` - Button container with gradient background
- `.o_form_custom_button` - Base button style (size, font, effects)
- `.o_form_button_save` - Green save button
- `.o_form_button_delete` - Red delete button  
- `.o_form_button_back` - Yellow back button

**Features**:
- Responsive design (desktop, tablet, mobile)
- Hover effects (lift & shadow)
- Focus states for accessibility
- Print media query (hides buttons when printing)
- Reduced motion support
- High contrast mode support

**Button Sizes**:
- Desktop: 220px × 75px
- Tablet: 180px × 65px
- Mobile: Full width × 70px

#### `static/src/js/form_buttons.js`

**Purpose**: Add JavaScript functionality

**Features**:
1. **Form Controller Patch**
   - Extends Odoo's FormController
   - Adds custom class to form views

2. **Keyboard Shortcuts**
   - `Ctrl+S` / `Cmd+S` → Save
   - `ESC` → Back (when not in modal/input)

3. **Utility Functions**
   - `setButtonLoading()` - Show loading state
   - `showButtonSuccess()` - Show success feedback

**Framework**: Odoo OWL (Odoo Web Library)

---

### Views Directory (`views/`)

#### `views/webclient_templates.xml`

**Purpose**: Load CSS and JS assets into Odoo backend

**Inherits**: `web.assets_backend`

**Note**: Actual asset loading is done via `__manifest__.py` → `assets` section

#### `views/form_view_examples.xml`

**Purpose**: Provide ready-to-use examples

**Includes Examples For**:
1. `res.partner` (Contacts) - Active by default
2. `sale.order` (Sales Orders) - Commented out
3. `account.move` (Invoices) - Commented out
4. Generic template for custom modules

**XPath Pattern**:
```xml
<xpath expr="//sheet" position="before">
    <!-- Buttons go here -->
</xpath>
```

This adds buttons BEFORE the sheet element (full width at top).

---

## 🔄 Data Flow

### 1. Module Loading
```
Odoo Startup
    ↓
Load __manifest__.py
    ↓
Import models/ (base_model.py)
    ↓
Load views/ (XML files)
    ↓
Load assets/ (CSS, JS)
    ↓
Module Ready
```

### 2. Button Click Flow

```
User clicks button
    ↓
Odoo triggers method (name="action_custom_save")
    ↓
Python method in base_model.py executes
    ↓
Method returns action dict
    ↓
Odoo processes action (notification/close form)
    ↓
User sees result
```

### 3. Asset Loading

```
User opens Odoo
    ↓
web.assets_backend template loads
    ↓
custom_buttons.css applied to all forms
    ↓
form_buttons.js adds functionality
    ↓
Buttons appear on form views
```

---

## 🎨 Customization Points

### 1. Button Colors
**File**: `static/src/css/custom_buttons.css`  
**Lines**: 60-95 (button color definitions)

### 2. Button Sizes
**File**: `static/src/css/custom_buttons.css`  
**Lines**: 35-42 (base button style)

### 3. Button Actions
**File**: `models/base_model.py`  
**Methods**: `action_custom_save()`, `action_custom_delete()`, `action_custom_back()`

### 4. Keyboard Shortcuts
**File**: `static/src/js/form_buttons.js`  
**Lines**: 25-45 (keyboard event listeners)

### 5. Which Forms Get Buttons
**File**: `views/form_view_examples.xml`  
**Action**: Add new `<record>` blocks for each model

---

## 🔐 Security

**No special security rules needed** because:
- Uses existing Odoo permissions
- `action_custom_delete()` respects model's unlink permissions
- `action_custom_save()` respects write permissions
- Inherits all security from base Odoo models

---

## 📦 Dependencies

### Required Modules
1. **base** (always installed)
   - Provides: Basic models, views, actions
   - Why: We extend the base model

2. **web** (always installed)
   - Provides: Web interface, assets framework
   - Why: We use web assets (CSS/JS)

### Optional Modules
- None (works standalone)

---

## 🔄 Upgrade Path

### From Version 1.0.0 to Future Versions

1. Backup your customizations
2. Update module files
3. Restart Odoo
4. Upgrade module from Apps menu
5. Clear assets cache
6. Test on a form view

---

## 🧪 Testing Checklist

- [ ] Module installs without errors
- [ ] Buttons appear on res.partner form
- [ ] Save button works (shows notification)
- [ ] Delete button works (asks confirmation, deletes record)
- [ ] Back button works (returns to list)
- [ ] Buttons look correct (Green, Red, Yellow)
- [ ] Responsive design works (test on mobile)
- [ ] Keyboard shortcuts work (Ctrl+S, ESC)
- [ ] No console errors (F12)
- [ ] Works with your custom modules

---

## 📊 Performance Impact

**Minimal Impact**:
- CSS: ~5KB (loaded once per session)
- JS: ~3KB (loaded once per session)
- Python: Negligible (simple method calls)
- Database: No additional tables or queries

**Optimizations**:
- CSS uses gradients instead of images
- JavaScript uses event delegation
- No external dependencies
- Assets are cached by browser

---

## 🌍 Localization

### To Translate Button Labels

Add to your module's `i18n/` directory:

```
i18n/
├── es.po          # Spanish
├── fr.po          # French
├── de.po          # German
└── your_lang.po   # Your language
```

Example `es.po`:
```po
msgid "SAVE"
msgstr "GUARDAR"

msgid "DELETE"
msgstr "ELIMINAR"

msgid "BACK"
msgstr "VOLVER"
```

Then update the XML to use translations:
```xml
<button ... string="SAVE">
    <i class="fa fa-save"/> <t t-esc="'SAVE'"/>
</button>
```

---

## 📝 Version History

### Version 1.0.0 (2025-12-21)
- ✅ Initial release
- ✅ Save, Delete, Back buttons
- ✅ Green, Red, Yellow colors
- ✅ Responsive design
- ✅ Keyboard shortcuts
- ✅ Example views for common models

---

## 🔮 Future Enhancements

Possible future features:
- [ ] Additional buttons (Print, Duplicate, Email)
- [ ] Button position options (top, bottom, side)
- [ ] Theme support (dark mode)
- [ ] Button groups/categories
- [ ] Custom button builder UI
- [ ] Per-user button preferences

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-21  
**Maintained By**: Your Company
