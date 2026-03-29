# Camera Provisioning Module for Odoo 17

## Overview

This module allows you to setup CCTV cameras via Bluetooth WiFi provisioning - exactly like the COFE app, but directly from your Odoo PWA!

## Features

- 📶 **Bluetooth WiFi Provisioning** - Configure camera WiFi via BLE
- 📹 **Camera Management** - Track all your CCTV cameras in Odoo
- 🔗 **RTSP URL Generation** - Automatic stream URL calculation
- 📱 **PWA Compatible** - Works on mobile devices

## Supported Cameras

- COFE PTZ Ball Cameras
- XiongMai (XM) based cameras
- Any camera with BLE WiFi provisioning (Service UUID: 0x1910)

## Requirements

### Browser
Web Bluetooth API requires:
- Google Chrome (recommended)
- Microsoft Edge
- Opera

**Note:** Safari and Firefox do NOT support Web Bluetooth.

### HTTPS
Web Bluetooth requires a secure connection. Your Odoo must be accessible via HTTPS.

## Installation

1. Copy the `camera_provisioning` folder to your Odoo addons directory:
   ```bash
   cp -r camera_provisioning /path/to/odoo/addons/
   ```

2. Update Odoo apps list:
   - Go to Apps → Update Apps List

3. Install the module:
   - Search for "Camera Provisioning"
   - Click Install

## Usage

### Adding a New Camera

1. Go to **📹 Cameras** menu
2. Click **📶 Scan New Camera**
3. Reset your camera (put it in pairing mode)
4. Click **"Scan for Camera"**
5. Select your camera from the browser popup (look for "XM" or "BallCamera")
6. Enter your WiFi credentials (use 2.4GHz network)
7. Click **"Connect Camera to WiFi"**
8. Wait for the camera to connect

### Managing Cameras

- View all cameras in Kanban or List view
- Click on a camera to see details and RTSP URLs
- Use the RTSP URL with VLC or your preferred player
- External RTSP URL works via your MikroTik DDNS

## BLE Protocol Details

The module uses these BLE characteristics (captured from nRF Connect):

| Component | UUID | Purpose |
|-----------|------|---------|
| Service | 0x1910 | WiFi Provisioning |
| Write Characteristic | 0x2B11 | Send WiFi credentials |
| Notify Characteristic | 0x2B10 | Receive status |

## MikroTik Router Setup

To access cameras remotely, configure your hAP ac²:

```routeros
# Enable Cloud DDNS
/ip cloud set ddns-enabled=yes

# Port forward to camera (replace 192.168.88.50 with camera IP)
/ip firewall nat add chain=dstnat dst-port=8554 protocol=tcp action=dst-nat to-addresses=192.168.88.50 to-ports=554

# Allow through firewall
/ip firewall filter add chain=forward dst-port=554 protocol=tcp action=accept place-before=0
```

## Troubleshooting

### "No camera found"
- Make sure camera is in pairing mode (reset it)
- Bring your phone/laptop closer to the camera
- Check that Bluetooth is enabled on your device

### "Web Bluetooth not supported"
- Use Chrome, Edge, or Opera browser
- Safari and Firefox don't support Web Bluetooth

### "HTTPS required"
- Access Odoo via https:// not http://
- For local testing, use localhost (treated as secure)

### Camera won't connect to WiFi
- Make sure you're using 2.4GHz WiFi (most cameras don't support 5GHz)
- Check WiFi password is correct
- Ensure camera is within WiFi range

## Developed By

Annapurna Travels
https://annapurnatravels.co.in

## License

LGPL-3
