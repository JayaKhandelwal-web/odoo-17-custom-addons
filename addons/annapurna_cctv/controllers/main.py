import json
import logging
import requests

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class CCTVController(http.Controller):

    # ─── PTZ Control API ────────────────────────────────────────────────────

    @http.route('/cctv/ptz/<int:camera_id>/<string:direction>',
                type='json', auth='user', methods=['POST'])
    def ptz_control(self, camera_id, direction, **kwargs):
        camera = request.env['cctv.camera'].browse(camera_id)
        if not camera.exists():
            return {'success': False, 'error': 'Camera not found'}

        step = camera.ptz_step
        actions = {
            'up':        (0, step, 0),
            'down':      (0, -step, 0),
            'left':      (-step, 0, 0),
            'right':     (step, 0, 0),
            'zoom_in':   (0, 0, step),
            'zoom_out':  (0, 0, -step),
            'stop':      None,
            'home':      'home',
        }

        if direction not in actions:
            return {'success': False, 'error': f'Unknown direction: {direction}'}

        action = actions[direction]
        if action is None:
            camera._onvif_ptz_stop()
        elif action == 'home':
            camera.action_ptz_home()
        else:
            pan, tilt, zoom = action
            camera._onvif_ptz_move(pan, tilt, zoom)

        return {'success': True, 'direction': direction}

    # ─── Snapshot Proxy ─────────────────────────────────────────────────────
    # Proxies the camera snapshot through Odoo so browser doesn't
    # need direct access to camera IP

    @http.route('/cctv/snapshot/<int:camera_id>',
                type='http', auth='user', methods=['GET'])
    def snapshot_proxy(self, camera_id, **kwargs):
        camera = request.env['cctv.camera'].browse(camera_id)
        if not camera.exists():
            return Response('Camera not found', status=404)

        snapshot_paths = [
            f'http://{camera.ip_address}:{camera.http_port}/onvif/snapshot',
            f'http://{camera.ip_address}:{camera.http_port}/snap.jpg',
            f'http://{camera.ip_address}:{camera.http_port}/snapshot.jpg',
            f'http://{camera.ip_address}:{camera.http_port}/image/jpeg.cgi',
            f'http://{camera.ip_address}:{camera.http_port}/cgi-bin/snapshot.cgi',
        ]

        auth = None
        if camera.username and camera.password:
            auth = (camera.username, camera.password)

        for url in snapshot_paths:
            try:
                resp = requests.get(url, auth=auth, timeout=5, stream=True)
                if resp.status_code == 200:
                    return Response(
                        resp.content,
                        content_type=resp.headers.get('Content-Type', 'image/jpeg'),
                        headers={
                            'Cache-Control': 'no-store, no-cache, must-revalidate',
                            'Pragma': 'no-cache',
                        }
                    )
            except Exception:
                continue

        return Response('Snapshot unavailable', status=503)

    # ─── Camera Status API ──────────────────────────────────────────────────

    @http.route('/cctv/status/<int:camera_id>',
                type='json', auth='user', methods=['POST'])
    def camera_status(self, camera_id, **kwargs):
        camera = request.env['cctv.camera'].browse(camera_id)
        if not camera.exists():
            return {'success': False, 'error': 'Camera not found'}

        status = camera._ping_camera()
        camera.write({'status': status})

        return {
            'success': True,
            'camera_id': camera_id,
            'name': camera.name,
            'status': status,
            'hls_url': camera.hls_url,
            'rtsp_url': camera.rtsp_url,
            'ptz_enabled': camera.ptz_enabled,
        }

    # ─── All Cameras Status ─────────────────────────────────────────────────

    @http.route('/cctv/all_status', type='json', auth='user', methods=['POST'])
    def all_cameras_status(self, **kwargs):
        cameras = request.env['cctv.camera'].search([('active', '=', True)])
        result = []
        for cam in cameras:
            result.append({
                'id': cam.id,
                'name': cam.name,
                'location': cam.location or '',
                'status': cam.status,
                'hls_url': cam.hls_url,
                'stream_type': cam.stream_type,
                'ptz_enabled': cam.ptz_enabled,
                'ip_address': cam.ip_address,
            })
        return {'success': True, 'cameras': result}
