import logging
import subprocess
import base64
import requests
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CCTVCamera(models.Model):
    _name = 'cctv.camera'
    _description = 'CCTV Camera'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # ─── Basic Info ────────────────────────────────────────────────────────────
    name = fields.Char(string='Camera Name', required=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, tracking=True)
    description = fields.Text()
    location = fields.Char(string='Physical Location', help='e.g. Main Gate, Server Room')
    image = fields.Binary(string='Camera Photo', attachment=True)

    # ─── Network Settings ──────────────────────────────────────────────────────
    ip_address = fields.Char(string='Camera IP Address', required=True, tracking=True,
                              help='Local IP via VPN tunnel e.g. 192.168.88.100 or 10.10.10.x')
    onvif_port = fields.Integer(string='ONVIF Port', default=80)
    rtsp_port = fields.Integer(string='RTSP Port', default=554)
    http_port = fields.Integer(string='HTTP Port', default=80)
    username = fields.Char(string='Username', default='admin')
    password = fields.Char(string='Password')

    # ─── Stream Settings ───────────────────────────────────────────────────────
    rtsp_path = fields.Char(string='RTSP Path', default='/Streaming/Channels/101',
                             help='Main stream path. Sub-stream usually /Streaming/Channels/102')
    rtsp_sub_path = fields.Char(string='RTSP Sub-stream Path', default='/Streaming/Channels/102')

    # MediaMTX / HLS settings
    mediamtx_host = fields.Char(string='MediaMTX Host', default='localhost',
                                 help='Host running MediaMTX for RTSP→HLS conversion')
    mediamtx_port = fields.Integer(string='MediaMTX HLS Port', default=8888)
    mediamtx_path = fields.Char(string='MediaMTX Stream Path', default='camera1',
                                 help='Stream name configured in mediamtx.yml')

    stream_type = fields.Selection([
        ('mediamtx_hls', 'MediaMTX HLS (Recommended)'),
        ('direct_rtsp', 'Direct RTSP (VLC/External)'),
        ('http_mjpeg', 'HTTP MJPEG Stream'),
        ('snapshot_refresh', 'Snapshot Auto-Refresh'),
    ], string='Stream Type', default='mediamtx_hls')

    mjpeg_path = fields.Char(string='MJPEG Path', default='/video.mjpg')

    # ─── PTZ Settings ──────────────────────────────────────────────────────────
    ptz_enabled = fields.Boolean(string='PTZ Enabled', default=False)
    ptz_step = fields.Float(string='PTZ Step Size', default=0.1,
                             help='Movement step 0.01 (small) to 1.0 (large)')

    # ─── Status ────────────────────────────────────────────────────────────────
    status = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('unknown', 'Unknown'),
    ], string='Status', default='unknown', compute='_compute_status', store=True)

    last_checked = fields.Datetime(string='Last Checked')
    last_snapshot = fields.Binary(string='Last Snapshot', attachment=True)
    last_snapshot_time = fields.Datetime(string='Snapshot Time')

    # ─── Recording ─────────────────────────────────────────────────────────────
    recording_ids = fields.One2many('cctv.recording', 'camera_id', string='Recordings')
    recording_count = fields.Integer(compute='_compute_recording_count')

    # ─── Computed URLs ─────────────────────────────────────────────────────────
    rtsp_url = fields.Char(string='RTSP URL', compute='_compute_urls')
    hls_url = fields.Char(string='HLS Stream URL', compute='_compute_urls')
    onvif_url = fields.Char(string='ONVIF URL', compute='_compute_urls')
    snapshot_url = fields.Char(string='Snapshot URL', compute='_compute_urls')

    # ──────────────────────────────────────────────────────────────────────────
    #  COMPUTE METHODS
    # ──────────────────────────────────────────────────────────────────────────

    @api.depends('recording_ids')
    def _compute_recording_count(self):
        for rec in self:
            rec.recording_count = len(rec.recording_ids)

    @api.depends('ip_address', 'rtsp_port', 'username', 'password', 'rtsp_path',
                 'mediamtx_host', 'mediamtx_port', 'mediamtx_path',
                 'http_port', 'mjpeg_path', 'onvif_port')
    def _compute_urls(self):
        for rec in self:
            auth = ''
            if rec.username and rec.password:
                auth = f'{rec.username}:{rec.password}@'
            elif rec.username:
                auth = f'{rec.username}@'

            rec.rtsp_url = f'rtsp://{auth}{rec.ip_address}:{rec.rtsp_port}{rec.rtsp_path or ""}'
            rec.hls_url = f'http://{rec.mediamtx_host}:{rec.mediamtx_port}/{rec.mediamtx_path or "camera1"}/index.m3u8'
            rec.onvif_url = f'http://{rec.ip_address}:{rec.onvif_port}/onvif/device_service'
            rec.snapshot_url = f'http://{auth}{rec.ip_address}:{rec.http_port}/onvif/snapshot'

    @api.depends('ip_address')
    def _compute_status(self):
        for rec in self:
            rec.status = rec._ping_camera()

    # ──────────────────────────────────────────────────────────────────────────
    #  NETWORK / STATUS METHODS
    # ──────────────────────────────────────────────────────────────────────────

    def _ping_camera(self):
        import socket as _socket
        for port in [self.onvif_port or 80, self.rtsp_port or 554]:
            try:
                s = _socket.create_connection((self.ip_address, port), timeout=5)
                s.close()
                return 'online'
            except Exception:
                continue
        return 'offline'

    def action_check_status(self):
        for rec in self:
            rec.status = rec._ping_camera()
            rec.last_checked = fields.Datetime.now()
            status_msg = '🟢 Camera is ONLINE' if rec.status == 'online' else '🔴 Camera is OFFLINE'
            rec.message_post(body=status_msg)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Status Check',
                'message': f'Status: {self.status.upper()}',
                'type': 'success' if self.status == 'online' else 'danger',
                'sticky': False,
            }
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  SNAPSHOT METHODS
    # ──────────────────────────────────────────────────────────────────────────

    def action_take_snapshot(self):
        """Take snapshot via HTTP (ONVIF snapshot URI or direct MJPEG frame)"""
        self.ensure_one()
        try:
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)

            # Try common snapshot URLs
            snapshot_paths = [
                f'http://{self.ip_address}:{self.http_port}/onvif/snapshot',
                f'http://{self.ip_address}:{self.http_port}/snap.jpg',
                f'http://{self.ip_address}:{self.http_port}/snapshot.jpg',
                f'http://{self.ip_address}:{self.http_port}/image/jpeg.cgi',
            ]

            image_data = None
            for url in snapshot_paths:
                try:
                    response = requests.get(url, auth=auth, timeout=5)
                    if response.status_code == 200 and response.content:
                        image_data = response.content
                        break
                except Exception:
                    continue

            if image_data:
                self.last_snapshot = base64.b64encode(image_data)
                self.last_snapshot_time = fields.Datetime.now()

                # Save as recording entry
                self.env['cctv.recording'].create({
                    'camera_id': self.id,
                    'name': f'Snapshot {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                    'recording_type': 'snapshot',
                    'snapshot_data': base64.b64encode(image_data),
                    'timestamp': fields.Datetime.now(),
                })

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': '📷 Snapshot Captured',
                        'message': 'Snapshot saved successfully!',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError('Could not capture snapshot. Check camera IP, port, and credentials.')

        except UserError:
            raise
        except Exception as e:
            raise UserError(f'Snapshot error: {str(e)}')

    # ──────────────────────────────────────────────────────────────────────────
    #  STREAM / VIEW ACTIONS
    # ──────────────────────────────────────────────────────────────────────────

    def action_open_stream(self):
        """Open live stream viewer"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'📹 {self.name} — Live Stream',
            'res_model': 'cctv.camera',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('annapurna_cctv.view_cctv_camera_stream_form').id,
            'target': 'new',
        }

    def action_view_recordings(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Recordings',
            'res_model': 'cctv.recording',
            'domain': [('camera_id', '=', self.id)],
            'view_mode': 'tree,form',
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  PTZ CONTROL (ONVIF)
    # ──────────────────────────────────────────────────────────────────────────

    def _onvif_ptz_move(self, pan, tilt, zoom=0.0):
        """Send PTZ ContinuousMove command via ONVIF SOAP"""
        self.ensure_one()
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:ptz="http://www.onvif.org/ver20/ptz/wsdl"
               xmlns:tt="http://www.onvif.org/ver10/schema">
  <soap:Header>
    <Security xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
      <UsernameToken>
        <Username>{self.username}</Username>
        <Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{self.password}</Password>
      </UsernameToken>
    </Security>
  </soap:Header>
  <soap:Body>
    <ptz:ContinuousMove>
      <ptz:ProfileToken>Profile_1</ptz:ProfileToken>
      <ptz:Velocity>
        <tt:PanTilt x="{pan}" y="{tilt}"/>
        <tt:Zoom x="{zoom}"/>
      </ptz:Velocity>
    </ptz:ContinuousMove>
  </soap:Body>
</soap:Envelope>"""
        try:
            response = requests.post(
                f'http://{self.ip_address}:{self.onvif_port}/onvif/PTZ',
                data=soap_body,
                headers={'Content-Type': 'application/soap+xml'},
                auth=(self.username, self.password),
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            _logger.warning(f'PTZ move failed: {e}')
            return False

    def _onvif_ptz_stop(self):
        """Stop PTZ movement"""
        self.ensure_one()
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:ptz="http://www.onvif.org/ver20/ptz/wsdl">
  <soap:Header>
    <Security xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
      <UsernameToken>
        <Username>{self.username}</Username>
        <Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{self.password}</Password>
      </UsernameToken>
    </Security>
  </soap:Header>
  <soap:Body>
    <ptz:Stop>
      <ptz:ProfileToken>Profile_1</ptz:ProfileToken>
    </ptz:Stop>
  </soap:Body>
</soap:Envelope>"""
        try:
            requests.post(
                f'http://{self.ip_address}:{self.onvif_port}/onvif/PTZ',
                data=soap_body,
                headers={'Content-Type': 'application/soap+xml'},
                auth=(self.username, self.password),
                timeout=5
            )
        except Exception as e:
            _logger.warning(f'PTZ stop failed: {e}')

    def action_ptz_up(self):
        self.ensure_one()
        self._onvif_ptz_move(0, self.ptz_step)
        return True

    def action_ptz_down(self):
        self.ensure_one()
        self._onvif_ptz_move(0, -self.ptz_step)
        return True

    def action_ptz_left(self):
        self.ensure_one()
        self._onvif_ptz_move(-self.ptz_step, 0)
        return True

    def action_ptz_right(self):
        self.ensure_one()
        self._onvif_ptz_move(self.ptz_step, 0)
        return True

    def action_ptz_zoom_in(self):
        self.ensure_one()
        self._onvif_ptz_move(0, 0, self.ptz_step)
        return True

    def action_ptz_zoom_out(self):
        self.ensure_one()
        self._onvif_ptz_move(0, 0, -self.ptz_step)
        return True

    def action_ptz_stop(self):
        self.ensure_one()
        self._onvif_ptz_stop()
        return True

    def action_ptz_home(self):
        """Go to PTZ home preset (preset 1)"""
        self.ensure_one()
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:ptz="http://www.onvif.org/ver20/ptz/wsdl">
  <soap:Header>
    <Security xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
      <UsernameToken>
        <Username>{self.username}</Username>
        <Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{self.password}</Password>
      </UsernameToken>
    </Security>
  </soap:Header>
  <soap:Body>
    <ptz:GotoHomePosition>
      <ptz:ProfileToken>Profile_1</ptz:ProfileToken>
    </ptz:GotoHomePosition>
  </soap:Body>
</soap:Envelope>"""
        try:
            requests.post(
                f'http://{self.ip_address}:{self.onvif_port}/onvif/PTZ',
                data=soap_body,
                headers={'Content-Type': 'application/soap+xml'},
                auth=(self.username, self.password),
                timeout=5
            )
        except Exception as e:
            _logger.warning(f'PTZ home failed: {e}')
        return True

    # ──────────────────────────────────────────────────────────────────────────
    #  ONVIF DEVICE INFO
    # ──────────────────────────────────────────────────────────────────────────

    def action_get_device_info(self):
        """Fetch camera device info via ONVIF"""
        self.ensure_one()
        soap_body = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
  <soap:Body>
    <tds:GetDeviceInformation/>
  </soap:Body>
</soap:Envelope>"""
        try:
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)

            response = requests.post(
                f'http://{self.ip_address}:{self.onvif_port}/onvif/device_service',
                data=soap_body,
                headers={'Content-Type': 'application/soap+xml'},
                auth=auth,
                timeout=8
            )
            if response.status_code == 200:
                self.message_post(body=f'📷 ONVIF Device Info:\n<pre>{response.text[:1000]}</pre>')
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': '✅ ONVIF Connected',
                        'message': 'Device info fetched — check chatter below.',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(f'ONVIF returned HTTP {response.status_code}')
        except UserError:
            raise
        except Exception as e:
            raise UserError(f'ONVIF connection failed: {str(e)}\n\nCheck IP, port, and credentials.')

    # ──────────────────────────────────────────────────────────────────────────
    #  CRON: Auto Status Check
    # ──────────────────────────────────────────────────────────────────────────

    @api.model
    def cron_check_all_cameras(self):
        cameras = self.search([('active', '=', True)])
        for cam in cameras:
            old_status = cam.status
            new_status = cam._ping_camera()
            cam.write({'status': new_status, 'last_checked': fields.Datetime.now()})
            if old_status != new_status:
                cam.message_post(body=f'Status changed: {old_status} → {new_status}')
        _logger.info(f'CCTV status check complete: {len(cameras)} cameras checked.')
