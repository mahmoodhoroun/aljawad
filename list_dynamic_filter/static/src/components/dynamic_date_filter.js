/** @odoo-module **/

import {Component, useState, xml} from "@odoo/owl";

export class ListDynamicDateFilter extends Component {
    static template = xml`
        <div class="o_list_dynamic_filter o_list_dynamic_date_filter d-flex align-items-center me-3 mb-2">
            <label t-att-for="props.fieldConfig.field_name" class="me-2 mb-0 fw-bold">
                <t t-esc="props.fieldConfig.name"/>:
            </label>
            <input
                type="date"
                class="form-control form-control-sm o_list_date_input"
                t-att-id="props.fieldConfig.field_name"
                t-model="state.selectedDate"
                t-on-change="onDateChange"
            />
        </div>
    `;

    static props = {
        fieldConfig: {type: Object},
        onValueSelected: {type: Function},
    };

    setup() {
        this.state = useState({
            selectedDate: "",
        });
    }

    onDateChange() {
        // Notify parent of date change
        this.props.onValueSelected(this.props.fieldConfig.field_name, {
            type: "date_single",
            date: this.state.selectedDate,
        });
    }
}
