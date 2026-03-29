/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

// Namespace the controller to avoid conflicts
export class TransportLogbookFormController extends FormController {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.action = useService("action");
        this.orm = useService("orm");
    }

    /**
     * @override
     */
    async saveRecord(record, options = {}) {
        const result = await super.saveRecord(record, options);
        
        // Only apply custom logic for transport logbook entries
        if (this.props.resModel === 'transport.logbook.entry' && result) {
            // Show notification
            this.notification.add(
                _t('Logbook entry has been saved successfully.'),
                {
                    title: _t('Entry Saved'),
                    type: 'success',
                }
            );
            
            // Check if we should auto-refresh (when not in dialog mode)
            if (this.model.root.mode === 'edit' && !this.isInDialog()) {
                // Auto-refresh with next entry data after a short delay
                setTimeout(() => {
                    this.createNextEntry();
                }, 1000);
            }
        }
        
        return result;
    }

    /**
     * Check if form is in dialog mode
     */
    isInDialog() {
        return this.env.isSmall || 
               document.querySelector('.modal.show') !== null ||
               this.props.mode === 'new';
    }

    /**
     * Create next entry with pre-filled data
     */
    async createNextEntry() {
        // Only proceed if we're working with transport logbook entries
        if (this.props.resModel !== 'transport.logbook.entry') {
            return;
        }
        
        const record = this.model.root;
        
        if (!record || !record.data) return;
        
        // Get current entry data
        const currentData = record.data;
        const nextDate = new Date(currentData.date);
        nextDate.setDate(nextDate.getDate() + 1);
        
        // Prepare default values for next entry
        let defaults = {
            vehicle_id: currentData.vehicle_id ? currentData.vehicle_id[0] : false,
            vehicle_type: currentData.vehicle_type,
            company_id: currentData.company_id ? currentData.company_id[0] : false,
            date: nextDate.toISOString().split('T')[0], // Format as YYYY-MM-DD
        };
        
        // Add vehicle type specific defaults
        if (currentData.vehicle_type === 'bus') {
            defaults.trip_number = currentData.trip_number || 0;
            defaults.running_km = currentData.running_km || 0.0;
            defaults.extra_distance = 0.0; // Always reset
            defaults.start_odometer = 0.0;
            defaults.end_odometer = 0.0;
        } else if (currentData.vehicle_type === 'cab') {
            defaults.trip_number = 0;
            defaults.running_km = 0.0;
            defaults.extra_distance = 0.0;
            defaults.start_odometer = currentData.end_odometer || 0.0; // Start from last end
            defaults.end_odometer = 0.0; // Always reset
        }
        
        // Create new record with defaults
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'transport.logbook.entry',
            view_mode: 'form',
            target: 'current',
            context: this.buildDefaultContext(defaults)
        });
    }

    /**
     * Build context with default values
     */
    buildDefaultContext(defaults) {
        const context = {};
        for (const key in defaults) {
            if (defaults.hasOwnProperty(key)) {
                context['default_' + key] = defaults[key];
            }
        }
        return context;
    }
    
    /**
     * Handle Save & New button clicks
     */
    async onSaveAndNew() {
        // Only work with transport logbook entries
        if (this.props.resModel !== 'transport.logbook.entry') {
            return super.saveRecord?.(this.model.root, { stayInEdition: false });
        }
        
        try {
            // First save the current record
            await this.saveRecord(this.model.root, { stayInEdition: false });
            
            // After successful save, create next entry
            setTimeout(() => {
                this.createNextEntry();
            }, 500);
        } catch (error) {
            console.error('Error saving record:', error);
        }
    }
}

export const transportLogbookFormView = {
    ...formView,
    Controller: TransportLogbookFormController,
};

// Only register if we're in the transport logbook context
const currentPath = window.location.pathname + window.location.search;
if (currentPath.includes('transport.logbook.entry') || 
    currentPath.includes('transport') ||
    document.querySelector('[data-model="transport.logbook.entry"]')) {
    
    // Use a namespaced registry key
    registry.category("views").add("transport_logbook.form", transportLogbookFormView);
    
    // Also register the original name but only if not taken and we're sure we're in the right context
    if (!registry.category("views").contains("logbook_form") && 
        window.location.search.includes('transport.logbook.entry')) {
        registry.category("views").add("logbook_form", transportLogbookFormView);
    }
}
