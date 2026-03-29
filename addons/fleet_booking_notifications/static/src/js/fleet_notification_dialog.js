/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

/**
 * FleetNotificationDialog
 * - Confirmed bookings shown first (sorted by controller)
 * - Clicking a card opens the fleet.booking form view
 */
export class FleetNotificationDialog extends Component {
    static template = "fleet_booking_notifications.NotificationDialog";
    static components = { Dialog };
    static props = {
        journeys: { type: Array },
        close: { type: Function },
    };

    setup() {
        this.action = useService("action");

        this.todayStr    = this._getDateStr(0);
        this.tomorrowStr = this._getDateStr(1);

        const hasToday = this.props.journeys.some(
            (j) => j.journey_start_date === this.todayStr
        );

        this.state = useState({
            activeTab: hasToday ? "today" : "week",
        });
    }

    // ─────────────────────────────────────────
    // Navigation – open booking form
    // ─────────────────────────────────────────

    async openBooking(journeyId) {
        // Close the popup first, then open the form
        this.props.close();
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "fleet.booking",
            res_id: journeyId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ─────────────────────────────────────────
    // Date helpers
    // ─────────────────────────────────────────

    _getDateStr(offsetDays = 0) {
        const d = new Date();
        d.setDate(d.getDate() + offsetDays);
        return d.toISOString().split("T")[0];
    }

    isToday(dateStr)    { return dateStr === this.todayStr; }
    isTomorrow(dateStr) { return dateStr === this.tomorrowStr; }

    // ─────────────────────────────────────────
    // Filtered journey lists
    // ─────────────────────────────────────────

    get todayJourneys()    { return this.props.journeys.filter((j) => j.journey_start_date === this.todayStr); }
    get tomorrowJourneys() { return this.props.journeys.filter((j) => j.journey_start_date === this.tomorrowStr); }
    get weekJourneys()     { return this.props.journeys; }

    get activeJourneys() {
        if (this.state.activeTab === "today")    return this.todayJourneys;
        if (this.state.activeTab === "tomorrow") return this.tomorrowJourneys;
        return this.weekJourneys;
    }

    // ─────────────────────────────────────────
    // Tab control
    // ─────────────────────────────────────────

    setTab(tab) { this.state.activeTab = tab; }

    // ─────────────────────────────────────────
    // Visual helpers
    // ─────────────────────────────────────────

    getStateBadgeClass(state) {
        const map = {
            confirmed: "fn-badge fn-badge-confirmed",
            enquiry:   "fn-badge fn-badge-enquiry",
            quotation: "fn-badge fn-badge-quotation",
            followup:  "fn-badge fn-badge-followup",
            completed: "fn-badge fn-badge-completed",
            cancelled: "fn-badge fn-badge-cancelled",
        };
        return map[state] || "fn-badge fn-badge-enquiry";
    }

    getDateChipLabel(dateStr) {
        if (this.isToday(dateStr))    return "TODAY";
        if (this.isTomorrow(dateStr)) return "TOMORROW";
        return "";
    }

    getCardClass(dateStr, state) {
        let base = "fn-journey-card";
        if (state === "confirmed") base += " fn-card-confirmed";
        if (this.isToday(dateStr))    return `${base} fn-card-today`;
        if (this.isTomorrow(dateStr)) return `${base} fn-card-tomorrow`;
        return base;
    }

    formatPrice(amount) {
        if (!amount) return "₹0";
        return "₹" + Number(amount).toLocaleString("en-IN");
    }

    onClose() { this.props.close(); }
}
