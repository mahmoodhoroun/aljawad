# Product Category Parent Updater

## Overview
This Odoo module adds functionality to update product category fields from their parent categories. It provides a convenient button in the product category list view to batch update selected categories.

## Features
- **Batch Update**: Button in the product category list view header to update multiple categories at once
- **Individual Update**: Button in the product category form view to update a single category
- **Field Synchronization**: Updates the following fields from parent to child categories:
  - `property_valuation`
  - `property_account_creditor_price_difference_categ`
  - `property_account_income_categ_id`
  - `property_account_expense_categ_id`
  - `property_stock_valuation_account_id`
  - `property_stock_journal`
  - `property_stock_account_input_categ_id`
  - `property_stock_account_output_categ_id`

## Installation
1. Copy the module to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the "Product Category Parent Updater" module

## Usage
### Batch Update (List View)
1. Navigate to Inventory > Configuration > Product Categories
2. Select the categories you want to update
3. Click the "Update from Parent" button in the header
4. Categories with parents will be updated, others will be skipped

### Individual Update (Form View)
1. Open a product category that has a parent
2. Click the "Update from Parent" button in the header
3. The category will be updated with values from its parent

## Dependencies
- `product`: Core product functionality
- `stock_account`: Stock accounting features

## Technical Details
- Extends the `product.category` model
- Adds two new methods: `action_update_from_parent()` and `action_update_all_from_parent()`
- Inherits existing views to add buttons
- Provides user notifications on completion
