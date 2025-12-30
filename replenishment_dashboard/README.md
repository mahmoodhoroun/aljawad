# Replenishment Dashboard

A high-performance dashboard module for tracking product replenishment with optimized SQL queries.

## Features

- **High Performance**: Uses direct SQL queries instead of ORM for fast data retrieval
- **Beautiful Dashboard**: Modern JavaScript interface with real-time filtering
- **Company Hierarchy**: Support for multi-company and branch filtering
- **Comprehensive Tracking**: Monitor stock levels, sales, purchases, and returns
- **Advanced Filtering**: Filter by company/branch, date ranges, and product search
- **Summary Statistics**: View totals for products, stock, orders, sales, and purchases
- **Sortable Columns**: Click on any column header to sort data
- **Pagination**: Handle large datasets efficiently with pagination
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Installation

1. Copy the `replenishment_dashboard` folder to your Odoo addons directory
2. Update the apps list in Odoo (Apps > Update Apps List)
3. Search for "Replenishment Dashboard" and install it

## Dependencies

- stock
- sale_management
- purchase
- web

## Usage

1. Navigate to: Replenishment Dashboard > Dashboard
2. Use filters to select:
   - Min/Max based on Company or Branch
   - Select specific branch (if Branch mode)
   - Set start and end dates
   - Search for specific products
3. View summary cards showing total metrics
4. Browse the data table with sortable columns
5. Use pagination to navigate through large datasets

## Technical Details

### Architecture

- **Frontend**: OWL (Odoo Web Library) JavaScript components
- **Backend**: Python controllers with optimized SQL queries
- **Data Flow**: AJAX requests to `/replenishment_dashboard/data` endpoint
- **Performance**: Single SQL query with CTEs (Common Table Expressions) for all calculations

### Key Files

- `controllers/main.py`: Backend endpoints with SQL queries
- `static/src/js/replenishment_dashboard.js`: OWL component
- `static/src/xml/replenishment_dashboard.xml`: Template
- `static/src/css/replenishment_dashboard.css`: Styles
- `views/replenishment_dashboard_views.xml`: Menu and action definitions

### SQL Optimization

The module uses a single optimized SQL query with multiple CTEs to calculate:
- Current stock quantities
- Start and end stock for date range
- Sales and sales returns
- Purchases and purchase returns
- Min/Max values from product configuration

This approach is significantly faster than using Odoo's ORM with computed fields.

## Configuration

Make sure to set min/max values on products using the `replenishment_report` module or directly on product fields:
- Company Min/Max Qty
- Branch Min/Max Qty

## License

LGPL-3

## Author

Your Company
