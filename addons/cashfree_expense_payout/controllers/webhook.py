# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

TRANSFER_STATE_LABELS = {
    'SUCCESS': 'success',
    'FAILED': 'failed',
    'REVERSED': 'failed',
    'PENDING': 'pending',
    'FLAGGED': 'pending',
}


class CashfreePayoutWebhook(http.Controller):

    @http.route(
        '/cashfree/payout/webhook',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def cashfree_payout_webhook(self, **kwargs):
        """
        Cashfree Payouts V2 webhook endpoint.

        Configure this URL in your Cashfree Merchant Dashboard:
        https://<your-odoo-domain>/cashfree/payout/webhook

        Cashfree sends a POST with transfer status on success/failure/reversal.
        """
        try:
            payload = json.loads(request.httprequest.data.decode('utf-8'))
        except Exception:
            payload = kwargs

        _logger.info('Cashfree Payout Webhook received: %s', payload)

        # ── Extract fields from webhook payload ──
        transfer_id = (
            payload.get('transfer_id')
            or payload.get('data', {}).get('transfer', {}).get('transfer_id')
        )
        cf_status = (
            payload.get('transfer_status')
            or payload.get('data', {}).get('transfer', {}).get('transfer_status', '')
        ).upper()

        utr = (
            payload.get('bank_account_utr')
            or payload.get('data', {}).get('transfer', {}).get('utr', '')
        )
        failure_reason = (
            payload.get('reason')
            or payload.get('data', {}).get('transfer', {}).get('reason', '')
        )

        if not transfer_id:
            _logger.warning('Cashfree webhook: No transfer_id in payload.')
            return request.make_response('Ignored: No transfer_id', headers={'Content-Type': 'text/plain'})

        # ── Find matching expense sheet ──
        sheet = request.env['hr.expense.sheet'].sudo().search(
            [('cashfree_payout_reference', '=', transfer_id)], limit=1
        )

        if not sheet:
            _logger.warning(
                'Cashfree webhook: No expense sheet found for transfer_id %s', transfer_id
            )
            return request.make_response('Not Found', headers={'Content-Type': 'text/plain'})

        odoo_state = TRANSFER_STATE_LABELS.get(cf_status, 'pending')
        vals = {
            'cashfree_payout_state': odoo_state,
            'cashfree_utr': utr,
            'cashfree_failure_reason': failure_reason if odoo_state == 'failed' else False,
        }
        sheet.write(vals)

        if odoo_state == 'success':
            sheet.message_post(
                body=(
                    '✅ <b>Cashfree Payout Confirmed via Webhook!</b><br/>'
                    '<b>UTR:</b> {utr}<br/>'
                    '<b>Amount:</b> ₹{amount} transferred to {employee}'
                ).format(
                    utr=utr,
                    amount=sheet.total_amount,
                    employee=sheet.employee_id.name,
                )
            )
        elif odoo_state == 'failed':
            sheet.message_post(
                body=(
                    '❌ <b>Cashfree Payout Failed (Webhook)!</b><br/>'
                    '<b>Reason:</b> {reason}'
                ).format(reason=failure_reason or 'Unknown')
            )
            sheet._notify_failure()

        _logger.info(
            'Cashfree webhook processed: sheet=%s, status=%s', sheet.name, odoo_state
        )
        return request.make_response('OK', headers={'Content-Type': 'text/plain'})
