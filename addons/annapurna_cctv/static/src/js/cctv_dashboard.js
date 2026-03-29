/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// ─── CCTV Dashboard Component ─────────────────────────────────────────────────

class CCTVDashboard extends Component {
    static template = "annapurna_cctv.Dashboard";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            cameras: [],
            loading: true,
            lastRefresh: null,
            selectedCamera: null,
            gridCols: 2,
        });

        this._refreshInterval = null;

        onMounted(() => {
            this._loadCameras();
            this._refreshInterval = setInterval(() => this._loadCameras(), 30000);
        });

        onWillUnmount(() => {
            if (this._refreshInterval) clearInterval(this._refreshInterval);
        });
    }

    async _loadCameras() {
        try {
            const result = await this.rpc("/cctv/all_status");
            if (result.success) {
                this.state.cameras = result.cameras;
                this.state.lastRefresh = new Date().toLocaleTimeString();
            }
        } catch (e) {
            console.error("CCTV Dashboard load error:", e);
        } finally {
            this.state.loading = false;
        }
    }

    async checkAllStatus() {
        this.state.loading = true;
        await this._loadCameras();
        this.notification.add("Status refreshed for all cameras", { type: "success" });
    }

    openCamera(cameraId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cctv.camera",
            res_id: cameraId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openStream(cameraId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cctv.camera",
            res_id: cameraId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: { stream_view: true },
        });
    }

    async takeSnapshot(cameraId, ev) {
        ev.stopPropagation();
        try {
            await this.rpc("/web/dataset/call_kw", {
                model: "cctv.camera",
                method: "action_take_snapshot",
                args: [[cameraId]],
                kwargs: {},
            });
            this.notification.add("Snapshot captured!", { type: "success" });
        } catch (e) {
            this.notification.add("Snapshot failed: " + e.message, { type: "danger" });
        }
    }

    setGridCols(cols) {
        this.state.gridCols = cols;
    }

    get onlineCount() {
        return this.state.cameras.filter(c => c.status === "online").length;
    }

    get offlineCount() {
        return this.state.cameras.filter(c => c.status === "offline").length;
    }

    get totalCount() {
        return this.state.cameras.length;
    }
}

CCTVDashboard.props = {};

registry.category("actions").add("cctv_dashboard", CCTVDashboard);
