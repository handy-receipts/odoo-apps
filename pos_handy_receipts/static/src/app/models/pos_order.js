/** @odoo-module */
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    serializeForORM() {
        const res = super.serializeForORM(...arguments);
        
        // Explicitly map the properties to the dictionary keys
        if (this.hr_data) {
            res.hr_delivery_type = this.hr_data.type || "";
            res.hr_delivery_value = this.hr_data.input_value || "";
        }
        
        return res;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        if (json.hr_qr_url) {
            this.hr_qr_url = json.hr_qr_url;
        }
    },
        // CRITICAL FIX: Export the URL to the Receipt Screen dictionary
    export_for_printing() {
        const receipt = super.export_for_printing(...arguments);
        receipt.hr_qr_url = this.hr_qr_url || false;
        return receipt;
    }

});