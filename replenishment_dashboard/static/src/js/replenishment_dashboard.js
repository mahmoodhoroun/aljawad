/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

console.log("Replenishment Dashboard JS file is loading...");

class ReplenishmentDashboard extends Component {
    static template = "replenishment_dashboard.Dashboard";

    setup() {
        this.state = useState({
            data: [],
            filters: {
                min_max_based_on: 'company',
                branch_id: null,
                start_date: this.getDefaultStartDate(),
                end_date: this.getDefaultEndDate(),
                product_ids: null,
            },
            branches: [],
            loading: false,
            initialLoading: true,
            backgroundLoading: false,
            sortField: 'product_name',
            sortOrder: 'asc',
            searchTerm: '',
            currentPage: 1,
            itemsPerPage: 50,
        });

        onWillStart(async () => {
            await this.loadBranches();
            // Load initial data quickly (first 100 products)
            await this.loadInitialData();
            // Then load all data in the background
            this.loadFullDataInBackground();
        });
    }

    getDefaultStartDate() {
        const date = new Date();
        date.setMonth(date.getMonth() - 1);
        return date.toISOString().split('T')[0];
    }

    getDefaultEndDate() {
        return new Date().toISOString().split('T')[0];
    }

    async loadBranches() {
        const result = await rpc('/replenishment_dashboard/branches', {});
        if (result.success) {
            this.state.branches = result.branches;
        }
    }

    async loadInitialData() {
        this.state.initialLoading = true;
        try {
            const result = await rpc('/replenishment_dashboard/data', {
                filters: { ...this.state.filters, limit: 100 }
            });
            if (result.success) {
                this.state.data = result.data;
            }
        } catch (error) {
            console.error('Error loading initial dashboard data:', error);
        } finally {
            this.state.initialLoading = false;
        }
    }

    async loadFullDataInBackground() {
        // Small delay to ensure UI is rendered first
        await new Promise(resolve => setTimeout(resolve, 100));

        this.state.backgroundLoading = true;
        try {
            const result = await rpc('/replenishment_dashboard/data', {
                filters: this.state.filters
            });
            if (result.success) {
                this.state.data = result.data;
                console.log(`Loaded ${result.data.length} products in total`);
            }
        } catch (error) {
            console.error('Error loading full dashboard data:', error);
        } finally {
            this.state.backgroundLoading = false;
        }
    }

    async loadData() {
        this.state.loading = true;
        try {
            const result = await rpc('/replenishment_dashboard/data', {
                filters: this.state.filters
            });
            if (result.success) {
                this.state.data = result.data;
            }
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        } finally {
            this.state.loading = false;
        }
    }

    async onFilterChange(field, event) {
        this.state.filters[field] = event.target.value || null;
        if (field === 'min_max_based_on' && event.target.value === 'company') {
            this.state.filters.branch_id = null;
        }
        await this.loadData();
    }

    async onDateChange(field, event) {
        this.state.filters[field] = event.target.value;
        await this.loadData();
    }

    async refreshData() {
        await this.loadData();
    }

    sortBy(field) {
        if (this.state.sortField === field) {
            this.state.sortOrder = this.state.sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            this.state.sortField = field;
            this.state.sortOrder = 'asc';
        }
    }

    get filteredData() {
        let data = [...this.state.data];

        // Apply search filter
        if (this.state.searchTerm) {
            const term = this.state.searchTerm.toLowerCase();
            data = data.filter(row =>
                (row.product_name && row.product_name.toLowerCase().includes(term)) ||
                (row.product_code && row.product_code.toLowerCase().includes(term))
            );
        }

        // Apply sorting
        data.sort((a, b) => {
            const aVal = a[this.state.sortField] || 0;
            const bVal = b[this.state.sortField] || 0;

            if (typeof aVal === 'string') {
                return this.state.sortOrder === 'asc'
                    ? aVal.localeCompare(bVal)
                    : bVal.localeCompare(aVal);
            } else {
                return this.state.sortOrder === 'asc'
                    ? aVal - bVal
                    : bVal - aVal;
            }
        });

        return data;
    }

    get paginatedData() {
        const start = (this.state.currentPage - 1) * this.state.itemsPerPage;
        const end = start + this.state.itemsPerPage;
        return this.filteredData.slice(start, end);
    }

    get totalPages() {
        return Math.ceil(this.filteredData.length / this.state.itemsPerPage);
    }

    get pageNumbers() {
        const pages = [];
        const total = this.totalPages;
        const current = this.state.currentPage;

        // Always show first page
        pages.push(1);

        // Show pages around current page
        for (let i = Math.max(2, current - 2); i <= Math.min(total - 1, current + 2); i++) {
            pages.push(i);
        }

        // Always show last page
        if (total > 1) {
            pages.push(total);
        }

        return [...new Set(pages)].sort((a, b) => a - b);
    }

    goToPage(page) {
        if (page >= 1 && page <= this.totalPages) {
            this.state.currentPage = page;
        }
    }

    onSearchChange(event) {
        this.state.searchTerm = event.target.value;
        this.state.currentPage = 1;
    }

    formatNumber(value) {
        return parseFloat(value || 0).toFixed(2);
    }

    get summaryStats() {
        const data = this.filteredData;
        return {
            totalProducts: data.length,
            totalOnHand: data.reduce((sum, row) => sum + (row.qty_on_hand || 0), 0),
            totalToOrder: data.reduce((sum, row) => sum + (row.to_order_qty || 0), 0),
            totalSales: data.reduce((sum, row) => sum + (row.sales_qty || 0), 0),
            totalPurchases: data.reduce((sum, row) => sum + (row.purchase_qty || 0), 0),
        };
    }

    getSortIcon(field) {
        if (this.state.sortField !== field) return '';
        return this.state.sortOrder === 'asc' ? '▲' : '▼';
    }

    get branchName() {
        if (!this.state.filters.branch_id) return '';
        const branch = this.state.branches.find(b => b.id == this.state.filters.branch_id);
        return branch ? branch.name : '';
    }

    exportToExcel() {
        const filtersJson = JSON.stringify(this.state.filters);
        const url = `/replenishment_dashboard/export_excel?filters=${encodeURIComponent(filtersJson)}`;
        window.open(url, '_blank');
    }
}

console.log("Registering ReplenishmentDashboard action...");
registry.category("actions").add("replenishment_dashboard.dashboard", ReplenishmentDashboard);
console.log("ReplenishmentDashboard action registered successfully!");

export default ReplenishmentDashboard;
