/** @odoo-module **/

import { registry } from "@web/core/registry";

// Get the user menu registry
const userMenuRegistry = registry.category("user_menuitems");

// Remove unwanted menu items
const itemsToRemove = ["documentation", "support", "odoo_account"];
for (const item of itemsToRemove) {
    userMenuRegistry.remove(item);
}

