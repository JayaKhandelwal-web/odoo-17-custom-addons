import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MyOperatorWebhook(http.Controller):
    
    @http.route('/myoperator/webhook', type='json', auth='none', methods=['POST'], csrf=False)
    def webhook_handler(self):
        """Handle webhooks from MyOperator"""
        try:
            data = request.jsonrequest
            _logger.info(f"MyOperator webhook received: {data}")
            
            # Process different webhook events
            event_type = data.get('event_type')
            
            if event_type == 'call_ended':
                self._handle_call_ended(data)
            elif event_type == 'call_started':
                self._handle_call_started(data)
            elif event_type == 'call_missed':
                self._handle_call_missed(data)
            
            return {'status': 'success'}
            
        except Exception as e:
            _logger.error(f"MyOperator webhook error: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def _handle_call_ended(self, data):
        """Handle call ended webhook"""
        call_data = data.get('call_data', {})
        
        # Find or create call log
        MyOperatorCallLog = request.env['myoperator.call.log'].sudo()
        
        call_log = MyOperatorCallLog.search([
            ('call_id', '=', call_data.get('id'))
        ], limit=1)
        
        vals = {
            'call_id': call_data.get('id'),
            'caller_number': call_data.get('caller_number'),
            'called_number': call_data.get('called_number'),
            'call_type': call_data.get('call_type'),
            'duration': call_data.get('duration', 0),
            'timestamp': call_data.get('timestamp'),
            'status': 'answered',
            'recording_url': call_data.get('recording_url'),
        }
        
        # Get active config
        config = request.env['myoperator.config'].sudo().search([('active', '=', True)], limit=1)
        if config:
            vals['config_id'] = config.id
        
        if call_log:
            call_log.write(vals)
        else:
            MyOperatorCallLog.create(vals)
    
    def _handle_call_started(self, data):
        """Handle call started webhook"""
        # Similar implementation for call started
        pass
    
    def _handle_call_missed(self, data):
        """Handle call missed webhook"""
        # Similar implementation for missed calls
        pass