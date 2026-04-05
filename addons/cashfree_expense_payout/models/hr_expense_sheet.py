# -*- coding: utf-8 -*-
import json
import logging
import requests
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

CASHFREE_URLS = {
    'sandbox': 'https://payout-gamma.cashfree.com/payout/v2',
    'production': 'https://payout.cashfree.com/payout/v2',
}

# Auth endpoint (v1) to get Bearer token
CASHFREE_AUTH_URLS = {
    'sandbox': 'https://payout-gamma.cashfree.com/payout/v1/authorize',
    'production': 'https://payout.cashfree.com/payout/v1/authorize',
}

TRANSFER_STATE_LABELS = {
    'SUCCESS': 'success',
    'FAILED': 'failed',
    'REVERSED': 'failed',
    'PENDING': 'pending',
    'FLAGGED': 'pending',
}


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    # ── Cashfree payout tracking fields ──────────────────────────────────────
    cashfree_transfer_id = fields.Char(
        string='Cashfree Transfer ID',
        readonly=True, copy=False,
        help='Unique transfer ID returned by Cashfree after initiating payout.',
    )
    cashfree_payout_state = fields.Selection(
        selection=[
            ('not_initiated', 'Not Initiated'),
            ('pending', 'Pending'),
            ('success', 'Success'),
            ('failed', 'Failed'),
        ],
        string='Cashfree Payout Status',
        default='not_initiated',
        readonly=True, copy=False,
    )
    cashfree_payout_reference = fields.Char(
        string='Cashfree Reference',
        readonly=True, copy=False,
        help='Internal unique reference sent to Cashfree for idempotency.',
    )
    cashfree_failure_reason = fields.Char(
        string='Failure Reason',
        readonly=True, copy=False,
    )
    cashfree_utr = fields.Char(
        string='UTR Number',
        readonly=True, copy=False,
        help='Bank UTR number after successful transfer.',
    )

    # ── Bank Account Verification fields ─────────────────────────────────────
    cashfree_bank_verified = fields.Selection(
        selection=[
            ('not_verified', 'Not Verified'),
            ('verified', 'Verified'),
            ('failed', 'Verification Failed'),
        ],
        string='Bank Verification Status',
        default='not_verified',
        readonly=True, copy=False,
        help='Status of bank account verification via Cashfree.',
    )
    cashfree_verified_name = fields.Char(
        string='Verified Account Holder Name',
        readonly=True, copy=False,
        help='Name returned by Cashfree after successful bank verification.',
    )
    cashfree_verify_message = fields.Char(
        string='Verification Message',
        readonly=True, copy=False,
        help='Message returned by Cashfree verification API.',
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_cashfree_config(self):
        """Fetch Cashfree credentials from system parameters."""
        ICP = self.env['ir.config_parameter'].sudo()
        client_id = ICP.get_param('cashfree_payout.client_id', '')
        client_secret = ICP.get_param('cashfree_payout.client_secret', '')
        environment = ICP.get_param('cashfree_payout.environment', 'sandbox')

        if not client_id or not client_secret:
            raise UserError(_(
                'Cashfree API credentials are not configured.\n'
                'Go to Settings \u2192 Cashfree Payout and enter your Client ID and Secret.'
            ))
        return {
            'client_id': client_id,
            'client_secret': client_secret,
            'base_url': CASHFREE_URLS.get(environment, CASHFREE_URLS['sandbox']),
            'auth_url': CASHFREE_AUTH_URLS.get(environment, CASHFREE_AUTH_URLS['sandbox']),
        }

    def _cashfree_get_token(self, config):
        """
        Step 1 of Cashfree Payouts V2 auth:
        POST to /payout/v1/authorize to get a short-lived Bearer token.
        """
        try:
            resp = requests.post(
                config['auth_url'],
                headers={
                    'X-Client-Id': config['client_id'],
                    'X-Client-Secret': config['client_secret'],
                    'Content-Type': 'application/json',
                },
                timeout=15,
            )
            resp_data = resp.json()
        except requests.exceptions.RequestException as e:
            raise UserError(_('Cashfree Auth Error: %s') % str(e))

        if resp.status_code == 200 and resp_data.get('status') == 'SUCCESS':
            token = resp_data.get('data', {}).get('token')
            if token:
                _logger.info('Cashfree: Bearer token obtained successfully.')
                return token

        error = resp_data.get('message', 'Unknown auth error')
        raise UserError(_(
            'Cashfree Authentication Failed: %s\n\n'
            'Check your Client ID and Secret in Settings \u2192 Cashfree Payout.'
        ) % error)

    def _cashfree_headers(self, config):
        """Returns auth headers using Bearer token (Payouts V2 OAuth)."""
        token = self._cashfree_get_token(config)
        return {
            'Authorization': 'Bearer {}'.format(token),
            'Content-Type': 'application/json',
        }

    def _get_beneficiary_id(self):
        """Build a stable beneficiary_id from employee id."""
        return 'EMP_{}'.format(self.employee_id.id)

    # ── Bank Account Verification ─────────────────────────────────────────────

    def action_verify_bank_account(self):
        """Verify employee bank account via Cashfree Payouts API."""
        self.ensure_one()
        employee = self.employee_id
        bank_account = employee.bank_account_id

        if not bank_account:
            raise UserError(_(
                'Employee "%s" has no bank account configured.\n'
                'Add one under Employee \u2192 Private Information \u2192 Private Banking.'
            ) % employee.name)

        acc_number = (bank_account.acc_number or '').replace(' ', '').replace('-', '')
        bank = bank_account.bank_id
        ifsc = bank.bic if bank else ''

        if not acc_number:
            raise UserError(_('Bank account number missing for "%s".' % employee.name))
        if not ifsc:
            raise UserError(_(
                'IFSC (BIC) missing on the bank for "%s".\n'
                'Edit the bank record and add the IFSC in the BIC field.' % employee.name
            ))

        config = self._get_cashfree_config()

        # Update: Use Bank Account Verification Sync V2 (POST)
        is_sandbox = 'gamma' in config['base_url']
        base_host = 'https://sandbox.cashfree.com' if is_sandbox else 'https://api.cashfree.com'
        verify_url = '{}/verification/bank-account/sync'.format(base_host)

        phone_str = employee.work_phone or employee.mobile_phone or '9999999999'
        phone_digits = "".join(filter(str.isdigit, phone_str))
        if len(phone_digits) < 8:
            phone_digits = '9999999999'
        
        payload = {
            'bank_account': acc_number,
            'ifsc': ifsc,
            'name': employee.name[:100],
            'phone': phone_digits,
        }

        headers = {
            'x-client-id': config['client_id'],
            'x-client-secret': config['client_secret'],
            'Content-Type': 'application/json',
        }

        _logger.info('Cashfree: Verifying bank account %s IFSC %s for %s via V2 Sync', acc_number, ifsc, employee.name)

        try:
            resp = requests.post(
                verify_url,
                headers=headers,
                json=payload,
                timeout=15,
            )
            resp_data = resp.json()
        except requests.exceptions.RequestException as e:
            raise UserError(_('Cashfree API error: %s') % str(e))

        _logger.info('Cashfree Bank Verification Response [%s]: %s', resp.status_code, resp_data)

        # Cashfree V2 Sync response handling
        if resp.status_code == 200 and resp_data.get('account_status'):
            account_status = resp_data.get('account_status')
            name_at_bank = resp_data.get('name_at_bank', '')
            msg = resp_data.get('account_status_code', '')

            if account_status == 'VALID':
                self.write({
                    'cashfree_bank_verified': 'verified',
                    'cashfree_verified_name': name_at_bank,
                    'cashfree_verify_message': msg or 'Verified successfully.',
                })
                self.message_post(body=_(
                    '<b>Bank Account Verified!</b><br/>'
                    'Employee: %s | Account: %s | IFSC: %s | Name at bank: %s'
                ) % (employee.name, acc_number, ifsc, name_at_bank or 'N/A'))
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Bank Account Verified'),
                        'message': _('Holder: %s | Acct: %s | IFSC: %s') % (
                            name_at_bank or 'N/A', acc_number, ifsc),
                        'type': 'success', 'sticky': False,
                    },
                }
            else:
                reason = resp_data.get('account_status_code') or resp_data.get('message') or 'Account could not be verified.'
                self.write({
                    'cashfree_bank_verified': 'failed',
                    'cashfree_verified_name': name_at_bank or '',
                    'cashfree_verify_message': reason,
                })
                self.message_post(body=_(
                    '<b>Bank Verification Failed!</b><br/>'
                    'Employee: %s | Account: %s | IFSC: %s | Reason: %s'
                ) % (employee.name, acc_number, ifsc, reason))
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Verification Failed'),
                        'message': reason,
                        'type': 'danger', 'sticky': True,
                    },
                }
        else:
            # Cashfree returned status=ERROR (e.g., sandbox limitation with real accounts)
            error_msg = resp_data.get('message', str(resp.text))
            _logger.warning('Cashfree bank verification API error: %s', error_msg)
            self.write({'cashfree_bank_verified': 'failed', 'cashfree_verify_message': error_msg})
            self.message_post(body=_(
                '<b>Bank Verification API Error</b><br/>'
                'Employee: %s | Account: %s | IFSC: %s<br/>'
                '<b>Cashfree Response:</b> %s<br/>'
                '<i>Note: If using Sandbox environment, real bank accounts cannot be validated. '
                'Switch to Production for real validation.</i>'
            ) % (employee.name, acc_number, ifsc, error_msg))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Bank Verification Error'),
                    'message': _('%s — If using Sandbox, switch to Production for real validation.') % error_msg,
                    'type': 'warning',
                    'sticky': True,
                },
            }

    # ── Cashfree API calls ────────────────────────────────────────────────────

    def _cashfree_create_beneficiary(self, config):
        """
        Register employee bank account as a Cashfree beneficiary.
        Safe to call multiple times — checks existence first.
        """
        employee = self.employee_id
        bank_account = employee.bank_account_id

        if not bank_account:
            raise UserError(_(
                'Employee "%s" does not have a bank account configured.\n'
                'Go to the employee form and add a bank account under '
                '"Private Information".' % employee.name
            ))

        beneficiary_id = self._get_beneficiary_id()

        # ── Check if beneficiary already exists ──
        check_url = '{}/beneficiary/{}'.format(config['base_url'], beneficiary_id)
        try:
            resp = requests.get(check_url, headers=self._cashfree_headers(config), timeout=15)
            if resp.status_code == 200:
                _logger.info('Cashfree: Beneficiary %s already exists.', beneficiary_id)
                return beneficiary_id
        except requests.exceptions.RequestException as e:
            _logger.warning('Cashfree: Could not check beneficiary existence: %s', e)

        # ── Create beneficiary ──
        partner = bank_account.partner_id or employee.work_contact_id or employee.address_home_id
        phone = employee.mobile_phone or employee.work_phone or ''
        email = employee.work_email or partner.email or ''

        # Strip spaces/dashes from account number
        acc_number = (bank_account.acc_number or '').replace(' ', '').replace('-', '')
        bank = bank_account.bank_id
        ifsc = bank.bic if bank else ''

        if not acc_number:
            raise UserError(_('Bank account number is missing for employee "%s".' % employee.name))
        if not ifsc:
            raise UserError(_(
                'IFSC code (BIC) is missing on the bank for employee "%s".\n'
                'Edit the bank and add the IFSC in the BIC field.' % employee.name
            ))

        payload = {
            'beneficiary_id': beneficiary_id,
            'beneficiary_name': employee.name,
            'beneficiary_instrument_details': {
                'bank_account_number': acc_number,
                'bank_ifsc': ifsc,
            },
            'beneficiary_contact_details': {
                'beneficiary_email': email,
                'beneficiary_phone': phone,
            },
        }

        create_url = '{}/beneficiary'.format(config['base_url'])
        try:
            resp = requests.post(
                create_url,
                headers=self._cashfree_headers(config),
                data=json.dumps(payload),
                timeout=15,
            )
            resp_data = resp.json()
        except requests.exceptions.RequestException as e:
            raise UserError(_('Cashfree API error while creating beneficiary: %s') % str(e))

        if resp.status_code in (200, 201):
            _logger.info('Cashfree: Beneficiary %s created successfully.', beneficiary_id)
            return beneficiary_id

        # Handle duplicate (already exists)
        if resp.status_code == 409:
            _logger.info('Cashfree: Beneficiary %s already exists (409).', beneficiary_id)
            return beneficiary_id

        error_msg = resp_data.get('message', resp.text)
        raise UserError(_('Cashfree: Failed to create beneficiary.\nError: %s') % error_msg)

    def _cashfree_initiate_transfer(self, config, beneficiary_id):
        """Initiate a standard payout transfer to the employee."""
        # Generate a unique reference for idempotency
        reference = 'EXP-{}-{}'.format(self.id, uuid.uuid4().hex[:8].upper())

        payload = {
            'transfer_id': reference,
            'transfer_amount': self.total_amount,
            'transfer_currency': 'INR',
            'beneficiary_details': {
                'beneficiary_id': beneficiary_id,
            },
            'transfer_remarks': 'Expense reimbursement: {}'.format(self.name),
        }

        transfer_url = '{}/transfers'.format(config['base_url'])
        try:
            resp = requests.post(
                transfer_url,
                headers=self._cashfree_headers(config),
                data=json.dumps(payload),
                timeout=15,
            )
            resp_data = resp.json()
        except requests.exceptions.RequestException as e:
            raise UserError(_('Cashfree API error while initiating transfer: %s') % str(e))

        if resp.status_code in (200, 201):
            cf_transfer_id = resp_data.get('transfer_id') or resp_data.get('cf_transfer_id', '')
            return reference, cf_transfer_id

        error_msg = resp_data.get('message', resp.text)
        raise UserError(_('Cashfree: Transfer initiation failed.\nError: %s') % error_msg)

    def _cashfree_get_transfer_status(self, config):
        """Fetch transfer status from Cashfree using stored reference."""
        if not self.cashfree_payout_reference:
            raise UserError(_('No Cashfree transfer reference found on this expense sheet.'))

        status_url = '{}/transfers/{}'.format(config['base_url'], self.cashfree_payout_reference)
        try:
            resp = requests.get(status_url, headers=self._cashfree_headers(config), timeout=15)
            resp_data = resp.json()
        except requests.exceptions.RequestException as e:
            raise UserError(_('Cashfree API error while fetching status: %s') % str(e))

        if resp.status_code == 200:
            return resp_data
        error_msg = resp_data.get('message', resp.text)
        raise UserError(_('Cashfree: Could not fetch transfer status.\nError: %s') % error_msg)

    # ── Main action: Pay via Cashfree ─────────────────────────────────────────

    def action_cashfree_pay(self):
        """
        Button action: Pay employee via Cashfree Payouts.
        - Only allowed on validated (post) expense sheets
        - Skips if already successfully paid
        """
        self.ensure_one()

        # ── Guard checks ──
        if self.state != 'post':
            raise UserError(_(
                'Only validated expense sheets can be paid via Cashfree.\n'
                'Current state: %s' % self.state
            ))
        if self.cashfree_payout_state == 'success':
            raise UserError(_('This expense sheet has already been successfully paid via Cashfree.'))
        if self.total_amount <= 0:
            raise UserError(_('Total amount must be greater than zero.'))

        config = self._get_cashfree_config()

        # Step 1: Create/verify beneficiary
        self.message_post(body=_('🔄 Initiating Cashfree payout for %s...') % self.employee_id.name)

        beneficiary_id = self._cashfree_create_beneficiary(config)

        # Step 2: Initiate transfer
        reference, cf_transfer_id = self._cashfree_initiate_transfer(config, beneficiary_id)

        # Step 3: Save state
        self.write({
            'cashfree_payout_reference': reference,
            'cashfree_transfer_id': cf_transfer_id,
            'cashfree_payout_state': 'pending',
            'cashfree_failure_reason': False,
        })

        self.message_post(
            body=_(
                '✅ Cashfree payout initiated successfully.<br/>'
                '<b>Reference:</b> %s<br/>'
                '<b>Employee:</b> %s<br/>'
                '<b>Amount:</b> ₹%s<br/>'
                '<b>Status:</b> Pending (awaiting bank confirmation)'
            ) % (reference, self.employee_id.name, self.total_amount)
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cashfree Payout Initiated'),
                'message': _('Transfer of ₹%s to %s is pending. Ref: %s') % (
                    self.total_amount, self.employee_id.name, reference
                ),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_cashfree_refresh_status(self):
        """Manual button to refresh transfer status from Cashfree."""
        self.ensure_one()
        if self.cashfree_payout_state not in ('pending',):
            raise UserError(_('Status refresh is only applicable for pending transfers.'))

        config = self._get_cashfree_config()
        resp_data = self._cashfree_get_transfer_status(config)

        cf_status = resp_data.get('transfer_status', '').upper()
        odoo_state = TRANSFER_STATE_LABELS.get(cf_status, 'pending')
        utr = resp_data.get('bank_account_utr') or resp_data.get('utr', '')
        failure_reason = resp_data.get('reason') or resp_data.get('failure_reason', '')

        vals = {
            'cashfree_payout_state': odoo_state,
            'cashfree_utr': utr,
            'cashfree_failure_reason': failure_reason if odoo_state == 'failed' else False,
        }
        self.write(vals)

        if odoo_state == 'success':
            self.message_post(
                body=_(
                    '✅ <b>Cashfree Payout Successful!</b><br/>'
                    '<b>UTR:</b> %s<br/>'
                    '<b>Amount:</b> ₹%s transferred to %s'
                ) % (utr, self.total_amount, self.employee_id.name)
            )
            # Auto-mark expense sheet as paid
            if self.state == 'post':
                self._do_approve()

        elif odoo_state == 'failed':
            self.message_post(
                body=_(
                    '❌ <b>Cashfree Payout Failed!</b><br/>'
                    '<b>Reason:</b> %s<br/>'
                    'Please retry or contact Cashfree support.'
                ) % (failure_reason or 'Unknown reason')
            )
            self._notify_failure()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Status Refreshed'),
                'message': _('Cashfree payout status: %s') % cf_status,
                'type': 'success' if odoo_state == 'success' else 'warning',
                'sticky': False,
            },
        }

    def _notify_failure(self):
        """Send failure notification email if configured."""
        ICP = self.env['ir.config_parameter'].sudo()
        notify_email = ICP.get_param('cashfree_payout.notify_email', '')
        if notify_email:
            template_vals = {
                'sheet_name': self.name,
                'employee': self.employee_id.name,
                'amount': self.total_amount,
                'reason': self.cashfree_failure_reason,
                'reference': self.cashfree_payout_reference,
            }
            subject = 'Cashfree Payout Failed: {}'.format(self.name)
            body = (
                'Cashfree payout failed for expense sheet: {sheet_name}<br/>'
                'Employee: {employee}<br/>'
                'Amount: ₹{amount}<br/>'
                'Reference: {reference}<br/>'
                'Reason: {reason}'
            ).format(**template_vals)
            mail = self.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body,
                'email_to': notify_email,
            })
            mail.send()

    def _do_approve(self):
        """Mark expense sheet as done after successful Cashfree payment."""
        try:
            self.action_sheet_move_create()
        except Exception:
            pass  # May already have journal entry

    # ── Computed display ──────────────────────────────────────────────────────

    @api.depends('cashfree_payout_state')
    def _compute_cashfree_state_label(self):
        labels = {
            'not_initiated': '⚪ Not Initiated',
            'pending': '🟡 Pending',
            'success': '🟢 Success',
            'failed': '🔴 Failed',
        }
        for rec in self:
            rec.cashfree_state_label = labels.get(rec.cashfree_payout_state, '')

    cashfree_state_label = fields.Char(
        string='Cashfree Status',
        compute='_compute_cashfree_state_label',
    )
