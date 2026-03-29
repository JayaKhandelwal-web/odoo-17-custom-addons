# Installation Guide - Universal Custom Big Buttons

## Quick Start (5 Minutes)

### Prerequisites

- Odoo 17.0 installed
- Access to Odoo addons directory
- Sudo/admin privileges (for server restart)

---

## 📥 Method 1: Manual Installation (Recommended)

### Step 1: Download/Copy the Module

```bash
# Navigate to your Odoo addons directory
cd /path/to/odoo/addons/

# If you have the module as a zip file
unzip odoo_custom_buttons.zip

# OR if you're copying from another location
cp -r /path/to/odoo_custom_buttons ./
```

### Step 2: Set Permissions

```bash
# Set correct ownership (replace 'odoo' with your Odoo user)
sudo chown -R odoo:odoo odoo_custom_buttons/

# Set correct permissions
sudo chmod -R 755 odoo_custom_buttons/
```

### Step 3: Verify Module Structure

```bash
# Check the module directory
ls -la odoo_custom_buttons/

# You should see:
# __init__.py
# __manifest__.py
# models/
# static/
# views/
# README.md
```

### Step 4: Restart Odoo

```bash
# If using systemd service
sudo systemctl restart odoo

# If using supervisor
sudo supervisorctl restart odoo

# If running manually
# Stop the server (Ctrl+C) and restart
./odoo-bin -c /path/to/odoo.conf
```

### Step 5: Update Apps List

1. Log in to Odoo as Administrator
2. Go to **Apps** menu
3. Click **Update Apps List** button (top-right)
4. Search for "**Universal Custom Big Buttons**"
5. Click **Install**

✅ Done! The module is now installed.

---

## 📥 Method 2: Docker Installation

If you're using Docker:

### Step 1: Copy Module to Docker Volume

```bash
# Find your Odoo addons volume
docker volume ls | grep addons

# Copy the module
docker cp odoo_custom_buttons/ your_odoo_container:/mnt/extra-addons/
```

### Step 2: Restart Container

```bash
# Restart the Odoo container
docker restart your_odoo_container
```

### Step 3: Install from Apps Menu

Follow Step 5 from Method 1 above.

---

## 📥 Method 3: Development Mode

For development/testing:

```bash
# Start Odoo with your addons path
./odoo-bin -c odoo.conf \
  --addons-path=/path/to/odoo/addons,/path/to/custom/addons \
  -d your_database \
  -u odoo_custom_buttons
```

---

## ✅ Verification

### Check Installation Success

1. Go to **Apps** → **Installed**
2. Search for "**Universal Custom Big Buttons**"
3. Status should show "Installed"

### Test the Buttons

1. Go to **Contacts** module
2. Open any contact (or create a new one)
3. You should see **GREEN, RED, and YELLOW** buttons at the top
4. Test each button:
   - **SAVE** → Shows success notification
   - **DELETE** → Shows confirmation dialog
   - **BACK** → Returns to list view

---

## 🔧 Add Buttons to More Modules

### For Your Custom Module (e.g., Fuel Logs)

Create a file in your module: `views/fuel_log_buttons.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_fuel_log_form_custom_buttons" model="ir.ui.view">
        <field name="name">fuel.log.form.custom.buttons</field>
        <field name="model">fuel.log</field>
        <field name="inherit_id" ref="your_fuel_module.view_fuel_log_form"/>
        <field name="arch" type="xml">
            <xpath expr="//sheet" position="before">
                <div class="o_form_custom_buttons_container">
                    <button name="action_custom_save" 
                            type="object" 
                            class="o_form_custom_button o_form_button_save">
                        <i class="fa fa-save"/> SAVE
                    </button>
                    <button name="action_custom_delete" 
                            type="object" 
                            class="o_form_custom_button o_form_button_delete"
                            confirm="Are you sure you want to delete this fuel log?">
                        <i class="fa fa-trash"/> DELETE
                    </button>
                    <button name="action_custom_back" 
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

Then add to your module's `__manifest__.py`:

```python
'depends': [
    'base',
    'odoo_custom_buttons',  # Add this dependency
],
'data': [
    # ... your other views
    'views/fuel_log_buttons.xml',  # Add this
],
```

Update your module:
```bash
# Upgrade your module
./odoo-bin -c odoo.conf -d your_database -u your_fuel_module
```

---

## 🐛 Common Issues & Solutions

### Issue 1: Module Not Found

**Problem**: Module doesn't appear in Apps list

**Solution**:
```bash
# 1. Check module is in correct directory
ls -la /path/to/odoo/addons/odoo_custom_buttons/

# 2. Check permissions
sudo chmod -R 755 odoo_custom_buttons/

# 3. Restart Odoo
sudo systemctl restart odoo

# 4. Update Apps List
# Apps → Update Apps List
```

### Issue 2: Buttons Not Showing

**Problem**: Module installed but buttons don't appear

**Solution**:
1. Clear browser cache (`Ctrl+Shift+R`)
2. Clear Odoo assets: Settings → Technical → Clear Assets Cache
3. Check view inheritance is added (see XML example above)
4. Restart browser completely

### Issue 3: Permission Denied

**Problem**: Cannot install module

**Solution**:
```bash
# Fix ownership and permissions
sudo chown -R odoo:odoo odoo_custom_buttons/
sudo chmod -R 755 odoo_custom_buttons/
```

### Issue 4: Import Error

**Problem**: Error about missing dependencies

**Solution**:
The module only depends on `base` and `web` which are always present.
If you see errors, ensure you're running Odoo 17.0 or compatible version.

---

## 📞 Need Help?

If you encounter any issues:

1. Check the **README.md** for detailed documentation
2. Review the **Troubleshooting** section
3. Check Odoo logs: `/var/log/odoo/odoo.log`
4. Contact support: support@yourcompany.com

---

## 🎉 Success!

If you can see the big GREEN, RED, and YELLOW buttons on your form views, congratulations! The module is successfully installed.

Now you can:
- ✅ Customize button colors in CSS
- ✅ Add buttons to more modules
- ✅ Modify button sizes and styles
- ✅ Enjoy easier form navigation!

---

**Happy Odoo-ing! 🚀**
