/** @odoo-module */
import { _t } from "@web/core/l10n/translation"; // Mandatory for Marketplace
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { useState, useEffect } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        const order = this.currentOrder;

        const extractPhone = (ord) => {
            if (!ord) return "";
            const partner = ord.getPartner ? ord.getPartner() : ord.partner;
            if (!partner) return "";
            const rawPhone = partner.phone || partner.mobile || "";
            return rawPhone.replace(/\D/g, '').slice(-10);
        };

        this.state = useState({ 
            deliveryType: 'mobile', 
            deliveryValue: extractPhone(order)  
        });

        // REACTIVE AUTO-FILL: Dependency should be a function returning the ID
        useEffect(
            () => {
                const phone = extractPhone(order);
                if (phone) { this.state.deliveryValue = phone; }
            },
            () => [this.currentOrder?.partner?.id] 
        );
    },

    async validateOrder(isForceValidate) {
        const order = this.currentOrder;
        const val = this.state.deliveryValue.trim();

        if (val) {
            if (this.state.deliveryType === 'mobile' && !/^\d{10}$/.test(val)) {
                this.env.services.notification.add(_t("Mobile Number must be exactly 10 digits."), { type: 'danger' });
                return; 
            }
            if (this.state.deliveryType === 'pairing_code' && !/^\d{4}$/.test(val)) {
                this.env.services.notification.add(_t("Pairing Code must be exactly 4 digits."), { type: 'danger' });
                return;
            }
        }

        if (order) {
            order.platform_data = {
                type: this.state.deliveryType,
                input_value: val
            };
        }
        return super.validateOrder(...arguments);
    }
});