# -*- coding: utf-8 -*-
# =============================================================================
#  Fleet Booking Reminder — Model Extension
#  Module : fleet_booking_reminder
#  File   : models/fleet_booking_reminder.py
#  Odoo   : 17.0  (Community & Enterprise)
#  Author : Raja — AlignTogether Solutions / Annapurna Tour & Travels
# =============================================================================
#
#  Extends fleet.booking with:
#
#  Fields
#  ──────
#  reminder_2day_sent        Boolean  — True once customer 2-day email is sent
#  reminder_2day_sent_date   Datetime — timestamp of that send
#  reminder_1day_sent        Boolean  — True once customer 1-day email is sent
#  reminder_1day_sent_date   Datetime — timestamp of that send
#
#  Scheduled Action (fires daily 08:00 AM IST / 02:30 UTC)
#  ────────────────────────────────────────────────────────
#  action_send_journey_reminders()
#      For every confirmed booking 2 days away  → ① customer email + ② manager brief
#      For every confirmed booking 1 day away   → ③ customer email + ④ manager alert
#
#  Private helpers
#  ───────────────
#  _send_customer_reminder(days)   — dispatches customer-facing template
#  _send_manager_brief(days)       — dispatches internal manager template
#
#  Manual re-send actions (form header buttons)
#  ─────────────────────────────────────────────
#  action_resend_customer_2day()
#  action_resend_customer_1day()
#  action_resend_manager_2day()    (fleet manager group only)
#  action_resend_manager_1day()    (fleet manager group only)
#
# =============================================================================

from odoo import api, fields, models, _
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class FleetBookingReminder(models.Model):
    _inherit = 'fleet.booking'

    # =========================================================================
    #  TRACKING FIELDS
    # =========================================================================

    reminder_2day_sent = fields.Boolean(
        string='2-Day Reminder Sent',
        default=False,
        readonly=True,
        copy=False,
        help='Automatically set to True once the 2-day customer reminder email is dispatched.',
    )
    reminder_2day_sent_date = fields.Datetime(
        string='2-Day Reminder Sent On',
        readonly=True,
        copy=False,
    )
    reminder_1day_sent = fields.Boolean(
        string='1-Day Reminder Sent',
        default=False,
        readonly=True,
        copy=False,
        help='Automatically set to True once the 1-day customer reminder email is dispatched.',
    )
    reminder_1day_sent_date = fields.Datetime(
        string='1-Day Reminder Sent On',
        readonly=True,
        copy=False,
    )

    # =========================================================================
    #  SCHEDULED ACTION — CRON ENTRY POINT
    # =========================================================================

    @api.model
    def action_send_journey_reminders(self):
        """
        Called daily by ir.cron (recommended: 08:00 AM IST / 02:30 UTC).

        Scans confirmed bookings and fires up to 4 emails per booking:

          2 days before journey_start_date:
            ① Customer 2-day reminder  (anti-duplicate via reminder_2day_sent)
            ② Manager  2-day prep brief

          1 day before journey_start_date:
            ③ Customer 1-day reminder  (anti-duplicate via reminder_1day_sent)
            ④ Manager  1-day final alert

        Returns True (required by Odoo cron code actions).
        """
        today          = date.today()
        two_days_later = today + timedelta(days=2)
        one_day_later  = today + timedelta(days=1)

        _logger.info(
            "[fleet_booking_reminder] Cron started — today: %s | "
            "2-day target: %s | 1-day target: %s",
            today, two_days_later, one_day_later,
        )

        # ── 2-Day Pass ─────────────────────────────────────────────────────
        bookings_2day = self.search([
            ('state',              '=', 'confirmed'),
            ('journey_start_date', '=', two_days_later),
            ('reminder_2day_sent', '=', False),
            ('customer_email',     '!=', False),
        ])
        _logger.info("[fleet_booking_reminder] 2-Day pass: %d booking(s)", len(bookings_2day))

        for booking in bookings_2day:
            booking._send_customer_reminder(days=2)
            booking._send_manager_brief(days=2)

        # ── 1-Day Pass ─────────────────────────────────────────────────────
        bookings_1day = self.search([
            ('state',              '=', 'confirmed'),
            ('journey_start_date', '=', one_day_later),
            ('reminder_1day_sent', '=', False),
            ('customer_email',     '!=', False),
        ])
        _logger.info("[fleet_booking_reminder] 1-Day pass: %d booking(s)", len(bookings_1day))

        for booking in bookings_1day:
            booking._send_customer_reminder(days=1)
            booking._send_manager_brief(days=1)

        _logger.info("[fleet_booking_reminder] Cron finished.")
        return True

    # =========================================================================
    #  PRIVATE — SEND CUSTOMER REMINDER
    # =========================================================================

    def _send_customer_reminder(self, days):
        """
        Resolves and sends the customer-facing reminder template.

        Template XML IDs (defined in data/fleet_booking_reminder_data.xml):
          fleet_booking_reminder.email_template_fleet_booking_reminder_2day
          fleet_booking_reminder.email_template_fleet_booking_reminder_1day

        On success:  sets reminder_Xday_sent flag + posts chatter note.
        On failure:  logs the error + posts a warning chatter note.

        :param days: int  — 2 or 1
        """
        self.ensure_one()

        template_map = {
            2: 'fleet_booking_reminder.email_template_fleet_booking_reminder_2day',
            1: 'fleet_booking_reminder.email_template_fleet_booking_reminder_1day',
        }
        xml_id = template_map.get(days)
        if not xml_id:
            _logger.error("[fleet_booking_reminder] No customer template mapped for days=%s", days)
            return

        template = self.env.ref(xml_id, raise_if_not_found=False)
        if not template:
            _logger.error(
                "[fleet_booking_reminder] Customer template not found: %s — "
                "is the data file loaded?", xml_id,
            )
            return

        if not self.customer_email:
            _logger.warning(
                "[fleet_booking_reminder] Skipping %s-day customer reminder "
                "for %s — customer_email is empty.", days, self.name,
            )
            return

        try:
            template.send_mail(self.id, force_send=True, raise_exception=True)
            now = fields.Datetime.now()

            if days == 2:
                self.write({'reminder_2day_sent': True, 'reminder_2day_sent_date': now})
            else:
                self.write({'reminder_1day_sent': True, 'reminder_1day_sent_date': now})

            self.message_post(
                body=_(
                    "📧 <b>%s-Day Customer Reminder</b> sent to "
                    "<b>%s</b> on %s"
                ) % (days, self.customer_email, now.strftime('%d %b %Y %H:%M')),
                message_type='notification',
            )
            _logger.info(
                "[fleet_booking_reminder] ✅ %s-day customer reminder sent "
                "— %s → %s", days, self.name, self.customer_email,
            )

        except Exception as exc:
            _logger.error(
                "[fleet_booking_reminder] ❌ %s-day customer reminder FAILED "
                "— %s: %s", days, self.name, exc,
            )
            self.message_post(
                body=_(
                    "⚠️ <b>Failed to send %s-Day Customer Reminder</b><br/>"
                    "Error: %s"
                ) % (days, exc),
                message_type='notification',
            )

    # =========================================================================
    #  PRIVATE — SEND MANAGER BRIEF
    # =========================================================================

    def _send_manager_brief(self, days):
        """
        Resolves and sends the internal manager email template.

        Recipient priority:
          1. object.user_id.email   (Assigned To on the booking)
          2. object.company_id.email

        No anti-duplicate flag — managers can always receive repeat briefs.

        Template XML IDs:
          fleet_booking_reminder.email_template_fleet_booking_manager_2day
          fleet_booking_reminder.email_template_fleet_booking_manager_1day

        :param days: int — 2 or 1
        """
        self.ensure_one()

        template_map = {
            2: 'fleet_booking_reminder.email_template_fleet_booking_manager_2day',
            1: 'fleet_booking_reminder.email_template_fleet_booking_manager_1day',
        }
        xml_id = template_map.get(days)
        if not xml_id:
            _logger.error("[fleet_booking_reminder] No manager template mapped for days=%s", days)
            return

        template = self.env.ref(xml_id, raise_if_not_found=False)
        if not template:
            _logger.error(
                "[fleet_booking_reminder] Manager template not found: %s — "
                "is the data file loaded?", xml_id,
            )
            return

        manager_name  = self.user_id.name if self.user_id else 'Fleet Manager'
        manager_email = (
            self.user_id.email
            if self.user_id and self.user_id.email
            else self.company_id.email
        )

        if not manager_email:
            _logger.warning(
                "[fleet_booking_reminder] Skipping %s-day manager brief for %s "
                "— no email on user '%s' or company.", days, self.name, manager_name,
            )
            self.message_post(
                body=_(
                    "⚠️ <b>%s-Day Manager Brief</b> could not be sent — "
                    "no email address found for <b>%s</b> or the company."
                ) % (days, manager_name),
                message_type='notification',
            )
            return

        try:
            template.send_mail(self.id, force_send=True, raise_exception=True)
            now = fields.Datetime.now()

            self.message_post(
                body=_(
                    "📋 <b>%s-Day Manager Brief</b> sent to "
                    "<b>%s</b> (%s) on %s"
                ) % (days, manager_name, manager_email, now.strftime('%d %b %Y %H:%M')),
                message_type='notification',
            )
            _logger.info(
                "[fleet_booking_reminder] ✅ %s-day manager brief sent "
                "— %s → %s", days, self.name, manager_email,
            )

        except Exception as exc:
            _logger.error(
                "[fleet_booking_reminder] ❌ %s-day manager brief FAILED "
                "— %s: %s", days, self.name, exc,
            )
            self.message_post(
                body=_(
                    "⚠️ <b>Failed to send %s-Day Manager Brief</b><br/>"
                    "Error: %s"
                ) % (days, exc),
                message_type='notification',
            )

    # =========================================================================
    #  PUBLIC — MANUAL RE-SEND ACTIONS  (form header buttons)
    # =========================================================================

    def action_resend_customer_2day(self):
        """Manually re-send the 2-day customer reminder. Resets the sent flag first."""
        self.ensure_one()
        self.write({'reminder_2day_sent': False})
        self._send_customer_reminder(days=2)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':   _('2-Day Customer Reminder Sent'),
                'message': _('Reminder email sent to %s.') % (self.customer_email or '—'),
                'type':    'success',
                'sticky':  False,
            },
        }

    def action_resend_customer_1day(self):
        """Manually re-send the 1-day customer reminder. Resets the sent flag first."""
        self.ensure_one()
        self.write({'reminder_1day_sent': False})
        self._send_customer_reminder(days=1)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':   _('1-Day Customer Reminder Sent'),
                'message': _('Reminder email sent to %s.') % (self.customer_email or '—'),
                'type':    'success',
                'sticky':  False,
            },
        }

    def action_resend_manager_2day(self):
        """Manually re-send the 2-day manager preparation brief."""
        self.ensure_one()
        self._send_manager_brief(days=2)
        email = (
            self.user_id.email
            if self.user_id and self.user_id.email
            else self.company_id.email or '—'
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':   _('Manager 2-Day Brief Sent'),
                'message': _('Internal preparation brief sent to %s.') % email,
                'type':    'success',
                'sticky':  False,
            },
        }

    def action_resend_manager_1day(self):
        """Manually re-send the 1-day manager final alert."""
        self.ensure_one()
        self._send_manager_brief(days=1)
        email = (
            self.user_id.email
            if self.user_id and self.user_id.email
            else self.company_id.email or '—'
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':   _('Manager 1-Day Alert Sent'),
                'message': _('Urgent internal alert sent to %s.') % email,
                'type':    'warning',
                'sticky':  False,
            },
        }
