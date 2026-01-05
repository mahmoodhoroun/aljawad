/** @odoo-module **/

import {Component, xml} from "@odoo/owl";
import {ListDynamicFilter} from "./dynamic_filter";
import {ListDynamicDateFilter} from "./dynamic_date_filter";
import {ListDynamicSelectionFilter} from "./dynamic_selection_filter";

export class ListDynamicFilterGroup extends Component {
    static template = xml`
        <div class="d-flex flex-wrap">
            <t t-foreach="props.filterFields" t-as="field" t-key="field.field_name">
                <t t-if="field.field_type === 'date' or field.field_type === 'datetime'">
                    <ListDynamicDateFilter
                        fieldConfig="field"
                        onValueSelected="(fieldName, value) => props.onFilterValueSelected(fieldName, value)"
                    />
                </t>
                <t t-elif="field.field_type === 'selection'">
                    <ListDynamicSelectionFilter
                        fieldConfig="field"
                        onValueSelected="(fieldName, value) => props.onFilterValueSelected(fieldName, value)"
                    />
                </t>
                <t t-else="">
                    <ListDynamicFilter
                        fieldConfig="field"
                        onValueSelected="(fieldName, value) => props.onFilterValueSelected(fieldName, value)"
                    />
                </t>
            </t>
        </div>
    `;
    static components = {ListDynamicFilter, ListDynamicDateFilter, ListDynamicSelectionFilter};
    static props = {
        filterFields: {type: Array},
        onFilterValueSelected: {type: Function},
    };
}
