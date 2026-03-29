/** @odoo-module **/

import { registry } from "@web/core/registry";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

// Namespace the controller to avoid conflicts
export class TransportLogbookVehicleDashboardController extends KanbanController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
    }

    /**
     * @override
     */
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        
        // Only add custom button if we're in the transport logbook context
        if (this.props.resModel === 'simply.fleet.vehicle') {
            // Add custom "New Entry" button
            menuItems.other.unshift({
                key: "transport_new_entry",
                description: _t("New Entry"),
                callback: () => this.onCreateQuickEntry(),
            });
        }
        
        return menuItems;
    }

    /**
     * Handler for the "New Entry" button
     */
    async onCreateQuickEntry() {
        try {
            // Get the last entry data for pre-filling
            const lastEntryData = await this.orm.call(
                "transport.logbook.entry",
                "get_last_entry_data",
                []
            );
            
            let context = {
                default_date: new Date().toISOString().split('T')[0]
            };
            
            // Add last entry data if available
            if (lastEntryData && Object.keys(lastEntryData).length > 0) {
                for (const key in lastEntryData) {
                    if (lastEntryData.hasOwnProperty(key)) {
                        context['default_' + key] = lastEntryData[key];
                    }
                }
            }
            
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'transport.logbook.entry',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: context
            });
            
        } catch (error) {
            // Fallback if RPC fails
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'transport.logbook.entry',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_date: new Date().toISOString().split('T')[0]
                }
            });
        }
    }
}

export const transportLogbookVehicleDashboardView = {
    ...kanbanView,
    Controller: TransportLogbookVehicleDashboardController,
};

// Only register if we're in the right context
const currentModel = window.location.search;
if (currentModel.includes('simply.fleet.vehicle') || 
    currentModel.includes('transport') ||
    document.querySelector('[data-model="simply.fleet.vehicle"]')) {
    
    // Use a namespaced registry key
    registry.category("views").add("transport_logbook.vehicle_dashboard_kanban", transportLogbookVehicleDashboardView);
    
    // Also register the original name but only if not already taken
    if (!registry.category("views").contains("vehicle_dashboard_kanban")) {
        registry.category("views").add("vehicle_dashboard_kanban", transportLogbookVehicleDashboardView);
    }
}
