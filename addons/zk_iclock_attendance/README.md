# ZKTeco iClock Attendance Integration for Odoo 17

## 🎉 CONGRATULATIONS!

Your custom module is ready! This module is built specifically for your WL20 device using the iClock protocol.

## ✅ What This Module Does

- ✅ **Automatic Attendance Tracking** - Real-time sync from WL20 to Odoo
- ✅ **Check-in/Check-out** - Automatic detection and pairing
- ✅ **Multiple Employees** - Unlimited employees supported
- ✅ **Multi-Device Support** - Connect multiple WL20 devices
- ✅ **Employee Management** - Push/delete employees from Odoo
- ✅ **Device Monitoring** - Connection status, last sync time
- ✅ **Reports** - Built-in attendance reports via Odoo HR
- ✅ **Dashboard** - Quick overview of devices and attendance

## 📦 Installation Steps

### 1. Install Module in Odoo

**Upload via UI (Recommended):**
```
1. Open Odoo as Administrator
2. Go to Apps menu
3. Click "Update Apps List"
4. Click "Upload" button
5. Select zk_iclock_attendance.zip
6. Click "Upload & Install"
```

**OR Install via Docker:**
```bash
# Copy to Odoo addons directory
sudo docker cp zk_iclock_attendance odoo17-docker-web-1:/mnt/extra-addons/

# Restart Odoo
sudo docker restart odoo17-docker-web-1

# Then in Odoo: Apps → Update Apps List → Search "ZKTeco iClock" → Install
```

### 2. Configure in Odoo

**A. Create Device:**
```
1. Go to: Attendance Devices → Configuration → Devices
2. Click "Create"
3. Fill in:
   - Name: Main Office WL20
   - Serial Number: RCED250200078
   - Location: Home Office
4. Click "Save"
5. Click "Show Configuration" to see device settings
```

**B. Configure Employees:**
```
1. Go to: Employees
2. Edit employee: Naman
3. Set:
   - Biometric ID: 1
   - Biometric Device: Main Office WL20
4. Click "Save"
```

### 3. Device is Already Configured!

Your WL20 is already configured with:
```
Serial Number: RCED250200078
Server: achievements-bond-donors-sold.trycloudflare.com
Port: 443 (or 80)
```

**No changes needed on device!** ✅

### 4. Start Odoo and Test

```bash
# Start Odoo Docker container
sudo docker start odoo17-docker-web-1

# Access Odoo
# Open: https://achievements-bond-donors-sold.trycloudflare.com
```

**Test Attendance:**
```
1. Scan your fingerprint on WL20
2. Go to: Attendance → Attendance Records
3. You should see new record within 10-30 seconds!
```

## 🎯 How It Works

```
WL20 Device (User scans finger)
    ↓
Internet
    ↓
Cloudflare Tunnel: achievements-bond-donors-sold.trycloudflare.com
    ↓
Odoo Docker Container (Port 8069)
    ↓
Module receives data at: /iclock/cdata
    ↓
Creates attendance record
    ↓
Shows in Odoo!
```

## 📊 Features Included

### Core Features
- ✅ Real-time attendance sync
- ✅ Automatic check-in/check-out
- ✅ Employee-device linking
- ✅ Device status monitoring
- ✅ Multiple device support

### Employee Management
- ✅ Push employees to device
- ✅ Delete employees from device
- ✅ Bulk operations
- ✅ Sync status tracking

### Reporting
- ✅ Attendance records view
- ✅ Device statistics
- ✅ Employee attendance history
- ✅ Export to Excel/PDF

### Admin Features
- ✅ Device configuration guide
- ✅ Connection status monitoring
- ✅ Command queue system
- ✅ Auto-disconnect detection

## 🔧 Troubleshooting

**Attendance not appearing?**
1. Check device Serial Number matches: `RCED250200078`
2. Check employee Biometric ID matches device User ID
3. Check Odoo Docker logs: `sudo docker logs odoo17-docker-web-1 | grep iClock`

**Device shows disconnected?**
1. Check Cloudflare tunnel is running
2. Restart WL20 device
3. Check device Cloud Server settings

**How to view logs?**
```bash
# Docker logs
sudo docker logs -f odoo17-docker-web-1

# Look for lines containing:
# - "iClock"
# - "ZKTeco"
# - Serial Number: RCED250200078
```

## 📋 Quick Reference

**Your Setup:**
- Device Serial: `RCED250200078`
- Device User ID (Naman): `1`
- Server URL: `achievements-bond-donors-sold.trycloudflare.com`
- Protocol: iClock Push
- Endpoints:
  - Attendance: `/iclock/cdata`
  - Commands: `/iclock/getrequest`

## 🚀 Next Steps

1. **Install module** (5 min)
2. **Create device record** (2 min)
3. **Configure employee** (1 min)
4. **Test attendance** (1 min)
5. **Add more employees** as needed
6. **Enjoy automated attendance!** 🎉

## 💡 Tips

- Keep Cloudflare tunnel running for continuous sync
- Employee Biometric ID must match device User ID
- Device will sync every few minutes automatically
- Can add multiple devices for different locations
- Use "Push to Device" button to sync employees
- Check device status in device list

## 📞 Support

If you need help:
1. Check Odoo logs for errors
2. Verify device Serial Number
3. Confirm employee Biometric ID
4. Test device connection (should show "Connected")

## 🎓 Adding More Employees

```
1. Register fingerprint on WL20:
   - Menu → User → New User
   - User ID: 2 (next number)
   - Register fingerprint

2. In Odoo:
   - Employees → Create/Edit
   - Biometric ID: 2 (same as device)
   - Biometric Device: Main Office WL20
   - Save

3. Done! Employee can now clock in/out
```

## ✨ Version Information

- **Module Version:** 2.0 (Standard - Full Featured)
- **Odoo Version:** 17.0
- **Protocol:** iClock Push
- **Device Tested:** ZKTeco WL20 (SN: RCED250200078)
- **Your Setup:** Docker + Cloudflare Tunnel

---

**READY TO USE!** Just install and start tracking attendance! 🚀
