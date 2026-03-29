from odoo import models, fields, api


class CCTVRecording(models.Model):
    _name = 'cctv.recording'
    _description = 'CCTV Recording / Snapshot'
    _order = 'timestamp desc'

    name = fields.Char(string='Name', required=True)
    camera_id = fields.Many2one('cctv.camera', string='Camera', required=True, ondelete='cascade')
    recording_type = fields.Selection([
        ('snapshot', 'Snapshot'),
        ('manual', 'Manual Recording'),
        ('motion', 'Motion Alert'),
        ('scheduled', 'Scheduled'),
    ], string='Type', default='snapshot')
    timestamp = fields.Datetime(string='Captured At', default=fields.Datetime.now)
    snapshot_data = fields.Binary(string='Snapshot Image', attachment=True)
    file_path = fields.Char(string='File Path', help='For server-side recordings')
    duration = fields.Integer(string='Duration (sec)', help='For video recordings')
    notes = fields.Text()
    active = fields.Boolean(default=True)

    def action_download_snapshot(self):
        self.ensure_one()
        if not self.snapshot_data:
            return
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/cctv.recording/{self.id}/snapshot_data/{self.name}.jpg?download=true',
            'target': 'self',
        }
