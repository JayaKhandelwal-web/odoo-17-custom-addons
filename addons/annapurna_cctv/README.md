# Annapurna CCTV Manager — Odoo 17 Module

Full CCTV camera integration for Odoo 17 Community Edition.
Built for Annapurna Travels infrastructure:
Camera → MikroTik → COFE Router → Internet → VPN → GCP Ubuntu → Odoo 17 Docker.

---

## Features

- **Multi-camera management** — Add unlimited ONVIF cameras
- **Live stream viewer** — HLS playback inside Odoo via MediaMTX
- **PTZ Control** — Pan, Tilt, Zoom, Home via ONVIF SOAP
- **Snapshot capture** — One-click snapshot, stored in Odoo
- **Dashboard** — Grid view of all cameras with live status
- **Auto status check** — Cron pings all cameras every 5 min
- **Recordings log** — All snapshots stored with timestamp

---

## Prerequisites

### 1. VPN Tunnel (MikroTik → GCP)
Ensure WireGuard/L2TP tunnel is active so GCP can reach camera IP.
Test: `ping 192.168.88.100` from GCP VM.

### 2. MediaMTX (RTSP → HLS transcoder)

Install on GCP VM (same server as Odoo):

```bash
# Download MediaMTX
wget https://github.com/bluenviron/mediamtx/releases/latest/download/mediamtx_v1.9.3_linux_amd64.tar.gz
tar xzf mediamtx_*.tar.gz
sudo mv mediamtx /usr/local/bin/
sudo mv mediamtx.yml /etc/mediamtx.yml
```

Edit `/etc/mediamtx.yml`:
```yaml
hlsAddress: :8888
rtspAddress: :8554

paths:
  camera1:
    source: rtsp://admin:YOUR_PASSWORD@192.168.88.100:554/Streaming/Channels/101
    sourceOnDemand: yes

  camera2:
    source: rtsp://admin:YOUR_PASSWORD@192.168.88.101:554/Streaming/Channels/101
    sourceOnDemand: yes
```

Run as service:
```bash
sudo tee /etc/systemd/system/mediamtx.service > /dev/null << 'SVC'
[Unit]
Description=MediaMTX RTSP/HLS Server
After=network.target

[Service]
ExecStart=/usr/local/bin/mediamtx /etc/mediamtx.yml
Restart=always

[Install]
WantedBy=multi-user.target
SVC

sudo systemctl enable mediamtx
sudo systemctl start mediamtx
```

Test HLS:
```
http://YOUR_GCP_IP:8888/camera1/index.m3u8
```

### 3. HLS.js in Odoo

Add to your Odoo Nginx config to allow CDN or download locally:

```bash
# Download HLS.js into module static folder
curl -L https://cdn.jsdelivr.net/npm/hls.js@latest/dist/hls.min.js \
  -o /opt/odoo/custom_addons/annapurna_cctv/static/src/js/hls.min.js
```

Then in `__manifest__.py` assets, add the file BEFORE cctv_stream_widget.js:
```python
'annapurna_cctv/static/src/js/hls.min.js',
```

### 4. GCP Firewall

Allow MediaMTX HLS port (internal only recommended):
```bash
# If Odoo and MediaMTX are on same VM, no firewall change needed
# If on different VMs:
gcloud compute firewall-rules create allow-mediamtx-internal \
  --allow tcp:8888 \
  --source-ranges 10.0.0.0/8
```

---

## Installation

```bash
# Copy module to Odoo addons path
cp -r annapurna_cctv /opt/odoo/custom_addons/

# Update Odoo addons list
docker exec -it odoo bash -c "odoo --update=annapurna_cctv --stop-after-init"

# Or restart and install from UI
docker restart odoo
```

In Odoo:
1. Go to **Settings → Apps → Update App List**
2. Search "Annapurna CCTV"
3. Click **Install**

---

## Adding Your First Camera

1. Go to **CCTV → Cameras → New**
2. Fill in:
   - **Name**: Main Gate
   - **Location**: Main Entrance
   - **IP Address**: 192.168.88.100 (camera's IP via VPN)
   - **Username / Password**: admin / your_password
   - **ONVIF Port**: 80
   - **RTSP Port**: 554
   - **RTSP Path**: /Streaming/Channels/101
   - **Stream Type**: MediaMTX HLS
   - **MediaMTX Host**: localhost (or GCP VM IP)
   - **MediaMTX Port**: 8888
   - **MediaMTX Stream Path**: camera1
3. Click **Ping Camera** to test connectivity
4. Click **Live Stream** to open viewer
5. Enable **PTZ** if your camera supports it

---

## Stream URL Formats by Camera Brand

| Brand        | RTSP Path                              |
|--------------|----------------------------------------|
| Hikvision    | /Streaming/Channels/101                |
| Dahua        | /cam/realmonitor?channel=1&subtype=0   |
| XiongMai     | /user=admin&password=&channel=1&stream=0.sdp |
| Generic ONVIF| /onvif/profile1/media.smp              |
| Reolink      | /h264Preview_01_main                   |

---

## Troubleshooting

**Camera shows Offline:**
- Check VPN tunnel is active: `ping 192.168.88.100` from GCP
- Check MikroTik port forward for camera IP

**Stream not loading:**
- Verify MediaMTX is running: `systemctl status mediamtx`
- Test HLS URL directly in browser
- Check MediaMTX logs: `journalctl -u mediamtx -f`

**PTZ not working:**
- Enable PTZ in camera settings
- Check camera supports ONVIF PTZ service
- Some cameras use Profile_2 — change in model code

**Snapshot fails:**
- Try different snapshot paths — varies by camera brand
- Check HTTP port (usually 80 or 8080)
- Some cameras need digest auth — update requests call in model
