/** @odoo-module **/

import {Component, useState, xml, onWillStart} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class ListDynamicSelectionFilter extends Component {
    static template = xml`
        <div class="o_list_dynamic_filter o_list_dynamic_selection_filter d-flex align-items-center me-3 mb-2">
            <label t-att-for="props.fieldConfig.field_name" class="me-2 mb-0 fw-bold">
                <t t-esc="props.fieldConfig.name"/>:
            </label>
            <select class="form-select form-select-sm o_list_selection_input"
                    t-att-id="props.fieldConfig.field_name"
                    t-model="state.selectedValue"
                    t-on-change="onSelectionChange">
                <option value="">-- Select --</option>
                <t t-foreach="state.selectionOptions" t-as="option" t-key="option[0]">
                    <option t-att-value="option[0]">
                        <t t-esc="option[1]"/>
                    </option>
                </t>
            </select>
        </div>
    `;

    static props = {
        fieldConfig: {type: Object},
        onValueSelected: {type: Function},
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            selectedValue: "",
            selectionOptions: [],
        });

        onWillStart(async () => {
            await this.loadSelectionOptions();
        });
    }

    async loadSelectionOptions() {
        // Get the field information from config
        const fieldName = this.props.fieldConfig.field_name;
        const fieldId = Array.isArray(this.props.fieldConfig.field_id)
            ? this.props.fieldConfig.field_id[0]
            : this.props.fieldConfig.field_id;

        try {
            // Get the field definition to extract selection values
            const fieldDef = await this.orm.read(
                'ir.model.fields',
                [fieldId],
                ['model', 'selection']
            );

            if (!fieldDef || fieldDef.length === 0) {
                console.error("Field definition not found for field_id:", fieldId);
                return;
            }

            const modelName = fieldDef[0].model;

            console.log("Field definition:", fieldDef[0]);
            console.log("Model name:", modelName);

            // Always use fields_get to get selection dynamically from the model
            // The 'selection' field in ir.model.fields stores it as a string representation
            // which is not reliable to parse, so we get it fresh from the model
            const fieldsGet = await this.orm.call(
                modelName,
                'fields_get',
                [[fieldName]],
                {attributes: ['selection', 'string']}
            );

            console.log("fields_get result:", fieldsGet);

            if (fieldsGet[fieldName] && fieldsGet[fieldName].selection) {
                // Selection is already in the format [[value, label], ...]
                this.state.selectionOptions = fieldsGet[fieldName].selection;
                console.log("Selection options loaded from fields_get:", this.state.selectionOptions);
            } else {
                console.log("No selection found for field:", fieldName, fieldsGet);
            }
        } catch (error) {
            console.error("Error loading selection options:", error);
        }
    }

    onSelectionChange(ev) {
        const value = ev.target.value;
        this.state.selectedValue = value;

        // Notify parent component about the selection change
        if (this.props.onValueSelected) {
            this.props.onValueSelected(this.props.fieldConfig.field_name, {
                type: "selection",
                value: value || false,
            });
        }
    }
}
