/** @odoo-module **/

import {ListRenderer} from "@web/views/list/list_renderer";
import {onWillStart, onMounted, mount} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {ListDynamicFilterGroup} from "./dynamic_filter_group";
import {patch} from "@web/core/utils/patch";

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.state = {
            filterConfig: null,
            viewId: this.env.config.viewId,
            filterFields: [],
            selectedFilters: {},
        };
        onWillStart(async () => {
            await this._loadFilterConfig();
        });
        onMounted(() => {
            if (this.__owl__ && this.__owl__.parent) {
                const el = this.__owl__.bdom.parentEl;
                if (el && this.state.filterFields.length > 0) {
                    // Find the list table wrapper or the list renderer element itself
                    let listTable = el.querySelector(".o_list_table_wrapper") || el.querySelector("table.o_list_table") || el;

                    // Check if filter already exists
                    let filterDiv = el.querySelector(".o_list_dynamic_filter_wrapper");

                    if (!filterDiv) {
                        filterDiv = document.createElement("div");
                        filterDiv.className = "o_list_dynamic_filter_wrapper";

                        // Insert the filter right before the list table
                        if (listTable && listTable.parentElement) {
                            listTable.parentElement.insertBefore(filterDiv, listTable);
                        } else {
                            // Fallback: insert at the beginning of the list renderer
                            if (el.firstChild) {
                                el.insertBefore(filterDiv, el.firstChild);
                            } else {
                                el.appendChild(filterDiv);
                            }
                        }

                        el.classList.add("has-dynamic-filters");

                        // The decision to mount the filters like this to the view was made after lots of testing.
                        // My initial idea was to inherit the ListRenderer and then xpath the filter component in.
                        // However, many models including sale.order, purchase.order etc. inherit the ListRenderer
                        // as primary extension mode. This causes our filter component to not show up for these models
                        // and thus leading to errors saying the filter config is missing.
                        // Another option was to inherit each models ListRenderer individually, but that would lead to
                        // a huge amount of code duplication, maintenance issues and also the extra work.
                        // Mounting the filter component like this ensures it works across all list views without any
                        // extra work.
                        mount(ListDynamicFilterGroup, filterDiv, {
                            props: {
                                filterFields: this.state.filterFields,
                                onFilterValueSelected: this.onFilterValueSelected.bind(this),
                            },
                            env: this.env,
                        });
                    }
                }
            }
        });
    },

    async _loadFilterConfig() {
        if (this.controls && this.controls.length > 1) return;
        const viewId = this.env.config.viewId;
        if (!viewId) return;
        const modelName = await this.orm.call("list.filter.config", "action_get_model_name_from_list_view_id", [
            viewId
        ]);
        if (!modelName) return;

        const configs = await this.orm.searchRead(
            "list.filter.config",
            [
                ["model_name", "=", modelName],
                ["active", "=", true],
            ],
            ["id", "filter_field_ids"]
        );

        if (configs && configs.length > 0) {
            const config = configs[0];
            const fields = await this.orm.searchRead(
                "list.filter.config.field",
                [["config_id", "=", config.id]],
                ["name", "field_name", "field_type", "comodel_name", "field_id", "config_id"]
            );

            this.state.filterConfig = config;
            this.state.filterFields = fields;
        }
    },

    async onFilterValueSelected(fieldName, value) {
        // Handle selection filters
        if (value && value.type === "selection") {
            this.state.selectedFilters[fieldName] = value;

            // Update all visible records with the selected value
            if (value.value !== false && this.props.list && this.props.list.records) {
                const recordIds = this.props.list.records.map(record => record.resId);
                if (recordIds.length > 0) {
                    const updateData = {};
                    updateData[fieldName] = value.value;

                    try {
                        await this.orm.write(
                            this.props.list.resModel,
                            recordIds,
                            updateData
                        );
                        // Reload the list to show updated computed fields
                        await this.props.list.load();
                    } catch (error) {
                        console.error("Failed to update selection field:", error);
                    }
                }
            }
        }
        // Handle date filters
        else if (value && value.type === "date_single") {
            this.state.selectedFilters[fieldName] = value;

            // Update all visible orderpoint records with the selected date
            if (value.date && this.props.list && this.props.list.records) {
                const recordIds = this.props.list.records.map(record => record.resId);
                if (recordIds.length > 0) {
                    const updateData = {};
                    updateData[fieldName] = value.date;

                    try {
                        await this.orm.write(
                            this.props.list.resModel,
                            recordIds,
                            updateData
                        );
                        // Reload the list to show updated computed fields
                        await this.props.list.load();
                    } catch (error) {
                        console.error("Failed to update date field:", error);
                    }
                }
            }
        } else {
            this.state.selectedFilters[fieldName] = {
                id: value.id,
                name: value.name || value.display_name,
            };
        }
        this._updateDomain();
    },

    _updateDomain() {
        if (!this.env.searchModel) return;

        const domain = [];
        const filterDescriptions = [];

        for (const [fieldName, value] of Object.entries(this.state.selectedFilters)) {
            const fieldConfig = this.state.filterFields.find((f) => f.field_name === fieldName);
            if (!fieldConfig) continue;

            // Handle date single filters - NO FILTERING LOGIC (as requested by user)
            // User will implement custom logic in the future
            if (value && value.type === "date_single") {
                // Do nothing - no filtering for date fields yet
                // User will add their own logic later
                continue;
            }
            // Handle many2one and many2many filters
            else if (value && value.id) {
                // Handle both many2one and many2many fields
                if (fieldConfig.field_type === "many2many") {
                    domain.push([fieldName, "in", [value.id]]);
                } else {
                    domain.push([fieldName, "=", value.id]);
                }
                filterDescriptions.push(`${fieldConfig.name}: ${value.name}`);
            }
        }

        // Clear existing filters and apply new ones
        if (domain.length > 0) {
            this.env.searchModel.facets.forEach((facet) => {
                this.env.searchModel.deactivateGroup(facet.groupId);
            });

            this.env.searchModel.createNewFilters([
                {
                    description: filterDescriptions.join(", "),
                    domain: domain,
                    type: "filter",
                },
            ]);
        } else {
            this.env.searchModel.facets.forEach((facet) => {
                this.env.searchModel.deactivateGroup(facet.groupId);
            });
        }
    },
});
