/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";
import { user } from "@web/core/user";
import { useState, onWillStart } from "@odoo/owl";

patch(SwitchCompanyMenu.prototype, {
    setup() {
        super.setup();
        this.state = useState({
            isRestrictedCompany: false
        });

        onWillStart(async () => {
            const hasGroup = await user.hasGroup("warehouse_selector_sale_orders.group_restrict_company_switch");
            console.log(" User restriction check:", hasGroup);
            this.state.isRestrictedCompany = hasGroup;
        });
    },

    get shouldShowMenu() {
        return !this.state.isRestrictedCompany;
    },

    get isSingleCompanyNew() {
        // If the user is restricted, disable the dropdown
        if (this.state.isRestrictedCompany) {
            return true;
        }
        // If the user only has one company, also disable
        return Object.values(this.companyService?.allowedCompaniesWithAncestors ?? {}).length <= 1;
    },
});