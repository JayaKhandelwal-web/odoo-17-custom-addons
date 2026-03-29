# Fleet Booking Invoice Archive - FIXED VERSION

## 🔧 What Was Fixed

### Issue
The PDF download/view URLs were returning **404 Not Found** errors because they used an incorrect URL structure for Odoo 17.

### Root Cause
The old URL format was:
```
/web/content/fleet.booking.invoice.document/{id}/pdf_file/{filename}
```

This format doesn't work properly in Odoo 17 because:
1. The model name in the URL path is not the correct Odoo routing pattern
2. Odoo 17 uses query parameters instead of path segments for web content

### Solution
Changed to the correct Odoo 17 URL structure:
```
/web/content?model=fleet.booking.invoice.document&id={id}&field=pdf_file&filename={filename}
```

## 📝 Changes Made

### File: `models/fleet_booking_invoice_document.py`

**1. Fixed `action_download_pdf` method:**

**Before:**
```python
def action_download_pdf(self):
    """Download the PDF file"""
    self.ensure_one()
    
    if not self.pdf_file:
        raise UserError("No PDF file available to download.")
    
    return {
        'type': 'ir.actions.act_url',
        'url': '/web/content/fleet.booking.invoice.document/{}/pdf_file/{}?download=true'.format(
            self.id, self.pdf_filename
        ),
        'target': 'new',
    }
```

**After:**
```python
def action_download_pdf(self):
    """Download the PDF file"""
    self.ensure_one()
    
    if not self.pdf_file:
        raise UserError("No PDF file available to download.")
    
    return {
        'type': 'ir.actions.act_url',
        'url': '/web/content?model=fleet.booking.invoice.document&id={}&field=pdf_file&filename={}&download=true'.format(
            self.id, self.pdf_filename
        ),
        'target': 'new',
    }
```

**2. Fixed `action_view_pdf` method:**

**Before:**
```python
def action_view_pdf(self):
    """View the PDF file in browser"""
    self.ensure_one()
    
    if not self.pdf_file:
        raise UserError("No PDF file available to view.")
    
    return {
        'type': 'ir.actions.act_url',
        'url': '/web/content/fleet.booking.invoice.document/{}/pdf_file/{}'.format(
            self.id, self.pdf_filename
        ),
        'target': 'new',
    }
```

**After:**
```python
def action_view_pdf(self):
    """View the PDF file in browser"""
    self.ensure_one()
    
    if not self.pdf_file:
        raise UserError("No PDF file available to view.")
    
    return {
        'type': 'ir.actions.act_url',
        'url': '/web/content?model=fleet.booking.invoice.document&id={}&field=pdf_file&filename={}'.format(
            self.id, self.pdf_filename
        ),
        'target': 'new',
    }
```

## 🎯 URL Structure Explanation

### Correct Odoo 17 Web Content URL Format

```
/web/content?model={model_name}&id={record_id}&field={field_name}&filename={filename}&download={true|false}
```

**Parameters:**
- `model`: The technical name of the model (e.g., `fleet.booking.invoice.document`)
- `id`: The database ID of the record
- `field`: The field name containing the binary data (e.g., `pdf_file`)
- `filename`: The desired filename for download
- `download`: Optional parameter to force download (`true`) vs. view in browser

### Examples

**Download PDF:**
```
/web/content?model=fleet.booking.invoice.document&id=5&field=pdf_file&filename=Invoice_ORD0041_Confirmed_20251216_084821.pdf&download=true
```

**View PDF in browser:**
```
/web/content?model=fleet.booking.invoice.document&id=5&field=pdf_file&filename=Invoice_ORD0041_Confirmed_20251216_084821.pdf
```

## 📦 Installation Instructions

1. **Remove old module (if installed):**
   ```bash
   # In Odoo shell or UI, uninstall the module first
   ```

2. **Copy this fixed module to your addons directory:**
   ```bash
   cp -r fleet_booking_invoice_archive /path/to/odoo/addons/
   ```

3. **Update the module list:**
   - Go to Apps menu
   - Click "Update Apps List"
   - Search for "Fleet Booking Invoice Archive"
   - Install or upgrade the module

4. **Test the fix:**
   - Open any fleet booking
   - Generate an invoice document
   - Click on the invoice document record
   - Test both "Download PDF" and "View PDF" buttons
   - URLs should now work correctly without 404 errors

## 🔍 Testing Checklist

- [ ] Download PDF button works correctly
- [ ] View PDF button opens in new tab
- [ ] No 404 errors in browser console
- [ ] PDF files are accessible
- [ ] Filename is preserved correctly
- [ ] Auto-generation still works on state changes
- [ ] Manual generation works from booking form
- [ ] Smart button shows correct count

## 📚 Additional Notes

### Why This Matters

The correct URL structure is crucial because:
1. **Security**: Proper routing ensures access control rules are applied
2. **Compatibility**: Works across different Odoo versions and configurations
3. **Reliability**: Uses Odoo's standard content delivery system
4. **Maintainability**: Aligns with Odoo's documented API

### Alternative Approaches (Not Recommended)

While there are other ways to serve binary content in Odoo, using `/web/content` is the standard and recommended approach because:
- It's the official Odoo way
- Handles access rights automatically
- Works with all storage backends (database, filestore, S3, etc.)
- Properly handles MIME types and encodings
- Supports both download and inline viewing

## 🐛 Troubleshooting

### Still Getting 404 Errors?

1. **Clear browser cache** - Old URLs might be cached
2. **Restart Odoo server** - Ensure code changes are loaded
3. **Check module installation** - Verify module is upgraded, not just installed
4. **Check file permissions** - Ensure Odoo can write attachments
5. **Check logs** - Look for errors in Odoo logs

### PDF Generation Issues?

1. **Verify report exists:**
   ```python
   self.env.ref('fleet_booking.action_report_fleet_booking_invoice')
   ```

2. **Check wkhtmltopdf installation:**
   ```bash
   which wkhtmltopdf
   wkhtmltopdf --version
   ```

3. **Review Odoo logs** for detailed error messages

## 📞 Support

For issues or questions:
- Check Odoo logs first: `/var/log/odoo/odoo.log`
- Verify module is properly upgraded
- Test with a simple booking first
- Contact: RAJA - Annapurna Tour & Travels

## 📄 License

LGPL-3

---

**Version:** 17.0.1.0.1 (Fixed)  
**Last Updated:** December 2025  
**Compatible with:** Odoo 17.0 Community Edition
