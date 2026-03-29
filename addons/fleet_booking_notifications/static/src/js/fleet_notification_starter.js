/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useEffect, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { FleetNotificationDialog } from "./fleet_notification_dialog";

/**
 * Session storage key.
 * Stores today's date string so the popup shows max once per day.
 */
const NOTIF_SESSION_KEY = "fleet_journey_notif_shown";

/**
 * FleetBookingNotificationStarter
 *
 * An invisible OWL component registered in the `main_components` registry.
 * It silently monitors navigation and automatically shows the upcoming-journey
 * popup whenever the user opens the Fleet Booking application.
 *
 * Detection strategy (multi-layered to handle both Odoo 17 clean-URL and
 * legacy hash-based routing):
 *   1. useEffect watching router.current  → fires on every navigation
 *   2. window hashchange / popstate       → backup for legacy routing
 *   3. onMounted setTimeout               → initial page load fallback
 *
 * Rate limiting: shown at most once per calendar day per browser session
 *               (tracked in sessionStorage).
 */
class FleetBookingNotificationStarter extends Component {
    static template = xml``;   // Renders nothing – purely functional
    static props = {};

    setup() {
        this.rpc    = useService("rpc");
        this.dialog = useService("dialog");
        this.menu   = useService("menu");
        this.router = useService("router");

        // ── 1. Reactive route watcher (main trigger) ──────────────────
        // useEffect deps function reads router.current (reactive in Odoo 17).
        // OWL re-runs the effect whenever the reactive value changes.
        useEffect(
            () => {
                this._checkAndShowNotification();
            },
            () => [
                // Support both Odoo 17 clean-URL pathname and legacy hash action
                this.router.current?.pathname,
                this.router.current?.hash?.action,
            ]
        );

        // ── 2. DOM navigation events (legacy routing backup) ──────────
        const onNavigate = () => {
            // Small delay lets Odoo update its menu state first
            setTimeout(() => this._checkAndShowNotification(), 600);
        };

        onMounted(() => {
            window.addEventListener("hashchange", onNavigate);
            window.addEventListener("popstate", onNavigate);

            // ── 3. Initial page-load check ─────────────────────────────
            // Covers the case where the user lands directly on Fleet Booking
            // (useEffect fires too but a slight delay ensures menu is ready)
            setTimeout(() => this._checkAndShowNotification(), 1500);
        });

        onWillUnmount(() => {
            window.removeEventListener("hashchange", onNavigate);
            window.removeEventListener("popstate", onNavigate);
        });
    }

    // ─────────────────────────────────────────────────────────────────
    // Core logic
    // ─────────────────────────────────────────────────────────────────

    /**
     * Main entry point.
     * Guards: must be in Fleet Booking app AND not yet shown today.
     */
    async _checkAndShowNotification() {
        try {
            if (!this._isFleetBookingApp()) return;
            if (this._isAlreadyShownToday()) return;

            // Mark BEFORE the async call to prevent duplicate dialogs
            // if this method is triggered rapidly (navigation events)
            this._markAsShownToday();

            const journeys = await this.rpc("/fleet_booking/upcoming_journeys", {});

            if (journeys && journeys.length > 0) {
                this.dialog.add(FleetNotificationDialog, { journeys });
            }
            // If no journeys – silently do nothing (don't show empty popup)

        } catch (err) {
            // Never break the UI – silently log
            console.warn("[FleetNotification] Could not load upcoming journeys:", err);
            // Reset the shown flag so user can retry on next navigation
            this._resetShownFlag();
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // Fleet Booking app detection
    // ─────────────────────────────────────────────────────────────────

    /**
     * Returns true if the user is currently inside the Fleet Booking application.
     * Checks URL (both clean and hash) and the active menu app.
     */
    _isFleetBookingApp() {
        // ── URL pathname check (Odoo 17 pushState routing) ────────────
        const pathname = (window.location.pathname || "").toLowerCase();
        if (pathname.includes("/fleet")) return true;

        // ── URL hash check (legacy / community routing) ───────────────
        const hash = (window.location.hash || "").toLowerCase();
        if (hash.includes("fleet_booking") || hash.includes("fleet-booking")) return true;

        // ── Active menu app check (most reliable) ─────────────────────
        try {
            const currentApp = this.menu.getCurrentApp();
            if (currentApp) {
                const xmlid = (currentApp.xmlid || "").toLowerCase();
                const name  = (currentApp.name  || "").toLowerCase();
                if (
                    xmlid.includes("fleet_booking") ||
                    xmlid.includes("fleet-booking") ||
                    name.includes("fleet booking") ||
                    name.includes("fleet")
                ) {
                    return true;
                }
            }
        } catch (_e) {
            // menu service may not be ready on very early load
        }

        return false;
    }

    // ─────────────────────────────────────────────────────────────────
    // Session storage helpers
    // ─────────────────────────────────────────────────────────────────

    _isAlreadyShownToday() {
        const stored = sessionStorage.getItem(NOTIF_SESSION_KEY);
        return stored === new Date().toDateString();
    }

    _markAsShownToday() {
        sessionStorage.setItem(NOTIF_SESSION_KEY, new Date().toDateString());
    }

    _resetShownFlag() {
        sessionStorage.removeItem(NOTIF_SESSION_KEY);
    }
}

// Register as a global invisible component loaded with the web client
registry.category("main_components").add("FleetBookingNotificationStarter", {
    Component: FleetBookingNotificationStarter,
});
