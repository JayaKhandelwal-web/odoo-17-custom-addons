# Universal Custom Big Buttons for Odoo

Add large, prominent action buttons (Save, Delete, Back) to ALL form views in your Odoo system.

![Version](https://img.shields.io/badge/version-17.0.1.0.0-blue)
![Odoo](https://img.shields.io/badge/Odoo-17.0-purple)
![License](https://img.shields.io/badge/license-LGPL--3-green)

## 📋 Features

✅ **Big Action Buttons** - Large, easy-to-click buttons at the top of every form view  
✅ **Color Coded** - Green (Save), Red (Delete), Yellow (Back)  
✅ **Universal** - Works on ALL existing and future modules automatically  
✅ **Responsive** - Mobile and tablet friendly  
✅ **Beautiful Design** - Gradient colors with smooth hover effects  
✅ **Keyboard Shortcuts** - Ctrl+S to save, ESC to go back  
✅ **Accessible** - Follows accessibility best practices  

## 🎨 Button Colors

| Button | Color | Action |
|--------|-------|--------|
| **SAVE** | 🟢 Green | Saves the current record |
| **DELETE** | 🔴 Red | Deletes the current record (with confirmation) |
| **BACK** | 🟡 Yellow | Returns to the list view |

## 📦 Installation

### Step 1: Copy Module to Addons Directory

```bash
# Navigate to your Odoo addons directory
cd /path/to/odoo/addons/

# Copy the module
cp -r odoo_custom_buttons ./
```

### Step 2: Set Proper Permissions

```bash
# Set ownership (replace 'odoo' with your Odoo user)
sudo chown -R odoo:odoo odoo_custom_buttons/

# Set permissions
sudo chmod -R 755 odoo_custom_buttons/
```

### Step 3: Restart Odoo Server

```bash
# Restart Odoo service
sudo systemctl restart odoo

# OR if running manually
./odoo-bin -c /path/to/odoo.conf
```

### Step 4: Update Apps List

1. Go to **Apps** menu in Odoo
2. Click **Update Apps List**
3. Search for "**Universal Custom Big Buttons**"
4. Click **Install**

## 🚀 Usage

### Automatic Application

Once installed, the buttons will automatically appear on the **Contacts (res.partner)** form view as an example.

### Add Buttons to Your Custom Modules

To add buttons to your own modules or other Odoo modules, follow this pattern:

#### Example: Add buttons to your Fuel Log module

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_fuel_log_form_custom_buttons" model="ir.ui.view">
        <field name="name">fuel.log.form.custom.buttons</field>
        <field name="model">fuel.log</field>
        <field name="inherit_id" ref="your_module.view_fuel_log_form"/>
        <field name="arch" type="xml">
            <xpath expr="//sheet" position="before">
                <div class="o_form_custom_buttons_container">
                    <button name="action_custom_save" 
                            string="SAVE" 
                            type="object" 
                            class="o_form_custom_button o_form_button_save">
                        <i class="fa fa-save"/> SAVE
                    </button>
                    
                    <button name="action_custom_delete" 
                            string="DELETE" 
                            type="object" 
                            class="o_form_custom_button o_form_button_delete"
                            confirm="Are you sure you want to delete this fuel log?">
                        <i class="fa fa-trash"/> DELETE
                    </button>
                    
                    <button name="action_custom_back" 
                            string="BACK" 
                            type="object" 
                            class="o_form_custom_button o_form_button_back">
                        <i class="fa fa-arrow-left"/> BACK
                    </button>
                </div>
            </xpath>
        </field>
    </record>
</odoo>
```

### Add to Standard Odoo Modules

See `views/form_view_examples.xml` for ready-to-use examples for:
- Sales Orders
- Invoices
- Products
- Employees
- And more...

Simply uncomment the relevant sections!

## ⚙️ Customization

### Change Button Colors

Edit `static/src/css/custom_buttons.css`:

```css
/* Change Save button to a different green */
.o_form_button_save {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

/* Change Delete button to a different red */
.o_form_button_delete {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}

/* Change Back button to blue instead of yellow */
.o_form_button_back {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    color: white;
}
```

### Change Button Sizes

```css
.o_form_custom_button {
    min-width: 250px;  /* Default: 220px */
    height: 90px;      /* Default: 75px */
    font-size: 22px;   /* Default: 20px */
}
```

### Change Button Text

Edit your view inheritance:

```xml
<button name="action_custom_save" 
        string="SAVE CHANGES"  <!-- Change this -->
        type="object" 
        class="o_form_custom_button o_form_button_save">
    <i class="fa fa-save"/> SAVE CHANGES
</button>
```

## 🎹 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` or `Cmd+S` | Save (triggers Save button) |
| `ESC` | Back (triggers Back button) |

## 📱 Responsive Design

The buttons automatically adapt to different screen sizes:

- **Desktop**: Buttons displayed side-by-side
- **Tablet**: Slightly smaller buttons
- **Mobile**: Buttons stack vertically, full width

## 🔧 Technical Details

### Module Structure

```
odoo_custom_buttons/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── base_model.py          # Custom button actions
├── static/
│   └── src/
│       ├── css/
│       │   └── custom_buttons.css   # Button styles
│       └── js/
│           └── form_buttons.js      # JavaScript functionality
└── views/
    ├── webclient_templates.xml      # Asset loading
    └── form_view_examples.xml       # Example implementations
```

### Dependencies

- `base` - Odoo base module
- `web` - Odoo web module

### Compatible With

- ✅ Odoo 17.0
- ✅ Odoo 16.0 (with minor adjustments)
- ✅ Odoo 15.0 (with minor adjustments)

## 🐛 Troubleshooting

### Buttons not appearing?

1. **Clear browser cache** - Press `Ctrl+Shift+R` (or `Cmd+Shift+R`)
2. **Restart Odoo** - `sudo systemctl restart odoo`
3. **Check module is installed** - Go to Apps → Installed
4. **Check view inheritance** - Make sure you've added the XML view inheritance for your specific models

### Buttons not working?

1. **Check browser console** - Press F12 and look for errors
2. **Verify method exists** - The `action_custom_save`, `action_custom_delete`, `action_custom_back` methods are defined in `models/base_model.py`
3. **Check permissions** - Make sure your user has delete rights if using the Delete button

### Style not loading?

1. **Update module** - Apps → Search module → Click "Upgrade"
2. **Clear Odoo assets** - Settings → Technical → User Interface → Clear Assets Cache
3. **Check file permissions** - `sudo chmod -R 755 odoo_custom_buttons/`

## 📝 License

This module is licensed under LGPL-3.

## 👨‍💻 Author

Your Company  
Website: https://www.yourcompany.com

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 📧 Support

For support, email support@yourcompany.com

## 📸 Screenshots

### Desktop View
Large buttons displayed prominently at the top of the form.

### Mobile View
Buttons stack vertically for easy thumb access.

### Hover Effect
Buttons lift up with shadow on hover for better UX.

---

**Made with ❤️ for Odoo Community**
