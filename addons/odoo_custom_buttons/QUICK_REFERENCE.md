# Quick Reference Guide

## 🎯 At a Glance

### Button Colors
- 🟢 **SAVE** - Green (`#28a745`)
- 🔴 **DELETE** - Red (`#dc3545`)
- 🟡 **BACK** - Yellow (`#ffc107`)

### Button Position
Full width at the top of the form (before `<sheet>`)

---

## 📋 Quick Copy-Paste Templates

### Template 1: Add to ANY Form View

```xml
<xpath expr="//sheet" position="before">
    <div class="o_form_custom_buttons_container">
        <button name="action_custom_save" type="object" 
                class="o_form_custom_button o_form_button_save">
            <i class="fa fa-save"/> SAVE
        </button>
        <button name="action_custom_delete" type="object" 
                class="o_form_custom_button o_form_button_delete"
                confirm="Are you sure?">
            <i class="fa fa-trash"/> DELETE
        </button>
        <button name="action_custom_back" type="object" 
                class="o_form_custom_button o_form_button_back">
            <i class="fa fa-arrow-left"/> BACK
        </button>
    </div>
</xpath>
```

### Template 2: Full View Inheritance Record

```xml
<record id="view_MODEL_form_custom_buttons" model="ir.ui.view">
    <field name="name">MODEL.form.custom.buttons</field>
    <field name="model">MODEL_NAME</field>
    <field name="inherit_id" ref="MODULE.view_form_id"/>
    <field name="arch" type="xml">
        <!-- Paste Template 1 here -->
    </field>
</record>
```

**Replace**:
- `MODEL` → your model name (e.g., `fuel_log`)
- `MODEL_NAME` → technical model name (e.g., `fuel.log`)
- `MODULE.view_form_id` → parent view reference (e.g., `your_module.view_fuel_log_form`)

---

## 🎨 Common Customizations

### Change Button Size

```css
/* File: static/src/css/custom_buttons.css */

.o_form_custom_button {
    min-width: 250px;   /* Default: 220px */
    height: 90px;       /* Default: 75px */
    font-size: 24px;    /* Default: 20px */
}
```

### Change Save Button Color to Blue

```css
.o_form_button_save {
    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
}
```

### Change Delete Button to Orange

```css
.o_form_button_delete {
    background: linear-gradient(135deg, #fd7e14 0%, #e8590c 100%);
}
```

### Change Back Button to Gray

```css
.o_form_button_back {
    background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
    color: white;  /* Change text to white for gray background */
}
```

### Make Buttons Bigger

```css
.o_form_custom_button {
    min-width: 300px;
    height: 100px;
    font-size: 24px;
}

.o_form_custom_button i {
    font-size: 28px;
}
```

### Remove Gradients (Solid Colors)

```css
.o_form_button_save {
    background: #28a745;  /* Solid green */
}

.o_form_button_delete {
    background: #dc3545;  /* Solid red */
}

.o_form_button_back {
    background: #ffc107;  /* Solid yellow */
}
```

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+S` (Windows/Linux)<br>`Cmd+S` (Mac) | Trigger SAVE button |
| `ESC` | Trigger BACK button |

To disable shortcuts, comment out the keyboard event listener in `static/src/js/form_buttons.js`.

---

## 🔍 Finding View IDs

### Method 1: Developer Mode

1. Enable Developer Mode: Settings → Activate Developer Mode
2. Go to the form view
3. Click the bug icon → View Metadata
4. Copy the "External ID"

### Method 2: XML ID

```bash
# Search in your module
grep -r "view_.*_form" your_module/views/
```

### Method 3: Database Query

```sql
SELECT id, name, xml_id 
FROM ir_ui_view 
WHERE model = 'your.model' 
  AND type = 'form';
```

---

## 📦 Module Dependencies

Add to your module's `__manifest__.py`:

```python
{
    'depends': [
        'base',
        'odoo_custom_buttons',  # Add this
    ],
}
```

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Buttons not visible | Clear cache: `Ctrl+Shift+R` |
| Style not loading | Settings → Technical → Clear Assets Cache |
| Module not found | Update Apps List |
| Permission error | `sudo chmod -R 755 odoo_custom_buttons/` |
| Buttons not working | Check browser console (F12) for errors |

---

## 📁 File Locations

```
odoo_custom_buttons/
├── models/base_model.py         ← Button actions
├── static/src/css/custom_buttons.css  ← Styles
├── static/src/js/form_buttons.js      ← JavaScript
└── views/form_view_examples.xml       ← Examples
```

---

## 🎯 Common Models to Add Buttons

### CRM / Sales
```python
'crm.lead'          # Leads/Opportunities
'sale.order'        # Sales Orders
'sale.order.line'   # Order Lines
```

### Accounting
```python
'account.move'      # Invoices/Bills
'account.payment'   # Payments
'account.journal'   # Journals
```

### Inventory
```python
'product.product'   # Products
'product.template'  # Product Templates
'stock.picking'     # Transfers
'stock.move'        # Stock Moves
```

### HR
```python
'hr.employee'       # Employees
'hr.leave'          # Time Off
'hr.expense'        # Expenses
```

### Contacts
```python
'res.partner'       # Contacts/Customers
'res.company'       # Companies
```

---

## 💡 Pro Tips

1. **Test First**: Add buttons to `res.partner` first to verify everything works
2. **One at a Time**: Add to one module, test, then add to others
3. **Keep Backups**: Always backup before making changes
4. **Version Control**: Use Git to track your customizations
5. **Documentation**: Document which forms have buttons in your project docs

---

## 📞 Support

**Email**: support@yourcompany.com  
**Docs**: See README.md for full documentation  
**Examples**: Check views/form_view_examples.xml

---

**Version**: 1.0.0  
**Last Updated**: 2025-12-21
