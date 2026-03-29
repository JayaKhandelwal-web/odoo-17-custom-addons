# Quick Installation Guide

## 🚀 Quick Start

### Step 1: Backup (Important!)
```bash
# Backup your database first
pg_dump your_database_name > backup_before_upgrade.sql
```

### Step 2: Install/Upgrade Module

#### Option A: Fresh Installation
```bash
# 1. Copy module to addons directory
cp -r fleet_booking_invoice_archive /path/to/odoo/addons/

# 2. Restart Odoo
sudo systemctl restart odoo

# 3. Update Apps List in Odoo UI
# Apps > Update Apps List

# 4. Install the module
# Apps > Search "Fleet Booking Invoice Archive" > Install
```

#### Option B: Upgrade Existing Module
```bash
# 1. Stop Odoo
sudo systemctl stop odoo

# 2. Backup the old module
mv /path/to/odoo/addons/fleet_booking_invoice_archive \
   /path/to/odoo/addons/fleet_booking_invoice_archive.old

# 3. Copy new fixed version
cp -r fleet_booking_invoice_archive /path/to/odoo/addons/

# 4. Restart Odoo
sudo systemctl restart odoo

# 5. Upgrade the module in UI
# Apps > Search "Fleet Booking Invoice Archive" > Upgrade
```

#### Option C: Command Line Upgrade (Faster)
```bash
# 1. Copy new module
cp -r fleet_booking_invoice_archive /path/to/odoo/addons/

# 2. Upgrade via command line
/path/to/odoo/odoo-bin -c /etc/odoo/odoo.conf \
  -d your_database_name \
  -u fleet_booking_invoice_archive \
  --stop-after-init

# 3. Restart Odoo
sudo systemctl restart odoo
```

## ✅ Verify Installation

### Test the Fix:

1. **Open a Fleet Booking**
   - Go to Fleet > Bookings
   - Open any existing booking or create a new one

2. **Generate Invoice Document**
   - Click "Generate Invoice (Current Stage)" button
   - Or change booking stage to trigger auto-generation

3. **Access Invoice Document**
   - Click on the smart button "Invoice Documents"
   - Open the generated invoice record

4. **Test PDF Access**
   - Click "Download PDF" button → Should download file
   - Click "View PDF" button → Should open in new tab
   - **No 404 errors should appear**

### Expected Results:
✅ PDF downloads successfully  
✅ PDF opens in browser  
✅ URL format: `/web/content?model=fleet.booking.invoice.document&id=X&field=pdf_file...`  
✅ No console errors  

## 🔧 Common Issues & Solutions

### Issue 1: Module Not Appearing in Apps List
**Solution:**
```bash
# Update apps list
# Settings > Apps > Update Apps List
# Then search again
```

### Issue 2: Still Getting 404 Errors After Upgrade
**Solution:**
```bash
# 1. Clear browser cache (Ctrl+Shift+Delete)
# 2. Restart Odoo in browser
# 3. Hard refresh (Ctrl+F5)
# 4. Check server logs for errors
tail -f /var/log/odoo/odoo.log
```

### Issue 3: Upgrade Button Not Working
**Solution:**
```bash
# Use command line upgrade
cd /path/to/odoo
./odoo-bin -c /etc/odoo/odoo.conf -d your_db -u fleet_booking_invoice_archive --stop-after-init
```

### Issue 4: Permission Denied Errors
**Solution:**
```bash
# Fix file permissions
sudo chown -R odoo:odoo /path/to/odoo/addons/fleet_booking_invoice_archive
sudo chmod -R 755 /path/to/odoo/addons/fleet_booking_invoice_archive
```

## 📋 File Structure Verification

Your module should have this structure:
```
fleet_booking_invoice_archive/
├── __init__.py
├── __manifest__.py
├── README.md
├── INSTALL.md (this file)
├── models/
│   ├── __init__.py
│   ├── fleet_booking_invoice_document.py (FIXED)
│   └── fleet_booking_inherit.py
├── views/
│   ├── fleet_booking_invoice_document_views.xml
│   ├── fleet_booking_views_inherit.xml
│   └── menu_items.xml
└── security/
    └── ir_model_access.csv
```

## 🎯 What Changed in This Version

The only changes are in `models/fleet_booking_invoice_document.py`:

1. **action_download_pdf()** - Fixed URL format
2. **action_view_pdf()** - Fixed URL format

Everything else remains the same.

## 📊 Migration from Old Version

If you have existing invoice documents, they will continue to work:
- Old records are preserved
- New downloads use fixed URLs
- No data migration needed
- Auto-generation continues to work

## 🔒 Security Note

The `/web/content` endpoint respects Odoo's access control:
- Users need read access to the record
- Model permissions are enforced
- No public access unless explicitly granted

## 🌐 Production Deployment

### Pre-Deployment Checklist:
- [ ] Tested on staging/development environment
- [ ] Database backup completed
- [ ] Module copied to production addons directory
- [ ] Odoo service scheduled for restart
- [ ] Users notified of brief downtime (if needed)

### Deployment Steps:
```bash
# 1. Backup
pg_dump production_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Copy module
scp -r fleet_booking_invoice_archive user@production:/opt/odoo/addons/

# 3. SSH to production
ssh user@production

# 4. Set permissions
sudo chown -R odoo:odoo /opt/odoo/addons/fleet_booking_invoice_archive

# 5. Upgrade module
sudo -u odoo /opt/odoo/odoo-bin -c /etc/odoo/odoo.conf \
  -d production_db -u fleet_booking_invoice_archive --stop-after-init

# 6. Restart Odoo
sudo systemctl restart odoo

# 7. Monitor logs
tail -f /var/log/odoo/odoo.log
```

## 💡 Tips

1. **Always test on development first**
2. **Keep backups before any upgrade**
3. **Clear browser cache after upgrade**
4. **Check logs for any warnings**
5. **Test with a sample booking before rolling out**

## 📞 Need Help?

If you encounter issues:
1. Check `/var/log/odoo/odoo.log` for errors
2. Verify module is properly upgraded (not just installed)
3. Ensure you're testing with a booking that has invoice documents
4. Clear browser cache and try again

---

**Quick Command Reference:**
```bash
# Restart Odoo
sudo systemctl restart odoo

# View Logs
tail -f /var/log/odoo/odoo.log

# Upgrade Module
./odoo-bin -c odoo.conf -d dbname -u fleet_booking_invoice_archive --stop-after-init

# Check Odoo Status
sudo systemctl status odoo
```
