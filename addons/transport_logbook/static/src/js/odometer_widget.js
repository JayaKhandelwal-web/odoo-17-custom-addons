/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState } from "@odoo/owl";
import { useInputField } from "@web/views/fields/input_field_hook";

// Namespace the component to avoid conflicts
export class TransportLogbookOdometerField extends Component {
    static template = "transport_logbook.OdometerField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.state = useState({
            value: this.props.record.data[this.props.name] || 0,
        });
        
        if (this.props.readonly) {
            return;
        }

        useInputField({
            getValue: () => this.state.value || 0,
            refName: "input",
            parse: (v) => this.parseValue(v),
        });
    }

    get formattedValue() {
        const value = this.props.record.data[this.props.name] || 0;
        return Math.round(value) + " KM";
    }

    get inputValue() {
        return Math.round(this.state.value || 0).toString();
    }

    parseValue(value) {
        if (typeof value === 'string') {
            value = value.replace(/[^\d.]/g, '');  // Allow digits and decimal point
        }
        return parseFloat(value) || 0;
    }

    onInput(ev) {
        // Handle input to allow only numbers (including decimals)
        let rawValue = ev.target.value;
        let numericValue = rawValue.replace(/[^\d.]/g, '');  // Allow digits and decimal point
        
        // Prevent multiple decimal points
        const parts = numericValue.split('.');
        if (parts.length > 2) {
            numericValue = parts[0] + '.' + parts.slice(1).join('');
        }
        
        // Update the input value
        ev.target.value = numericValue;
        this.state.value = this.parseValue(numericValue);
    }

    onChange(ev) {
        const parsedValue = this.parseValue(ev.target.value);
        this.state.value = parsedValue;
        this.props.record.update({ [this.props.name]: parsedValue });
    }
}

// Only register if we're in the transport_logbook module context
// Check if we're actually in a view that needs this widget
const currentModule = window.location.pathname;
if (currentModule.includes('transport') || 
    document.querySelector('[data-module="transport_logbook"]') ||
    window.odoo?.session?.user_context?.active_model === 'transport.logbook.entry') {
    
    // Use a namespaced registry key to avoid conflicts
    registry.category("fields").add("transport_logbook.odometer", TransportLogbookOdometerField);
    
    // Also register with the simple name but only in our module context
    if (!registry.category("fields").contains("odometer")) {
        registry.category("fields").add("odometer", TransportLogbookOdometerField);
    }
}
