/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class PhoneWidget extends Component {
    setup() {
        this.notification = useService("notification");
    }

    async makeCall(phoneNumber) {
        try {
            // This would integrate with MyOperator's click-to-call API
            // For now, we'll show a notification
            this.notification.add(
                `Initiating call to ${phoneNumber}...`,
                { type: "info" }
            );
            
            // Here you would make the actual API call to MyOperator
            // const response = await this.rpc('/myoperator/make_call', {
            //     phone_number: phoneNumber
            // });
            
        } catch (error) {
            this.notification.add(
                "Failed to initiate call",
                { type: "danger" }
            );
        }
    }
}

PhoneWidget.template = "myoperator_integration.PhoneWidget";

registry.category("fields").add("phone_widget", PhoneWidget);