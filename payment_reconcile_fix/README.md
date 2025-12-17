# Payment Reconcile Fix

## Overview
This module fixes reconciliation mismatches between payments and invoices in the auto_reconcile_payment module. It provides a script that ensures data consistency between payment reconcile amounts and actual invoice reconciliations.

## Features
- **Reset Payment Reconcile Amounts**: Sets all payment reconcile amounts to 0 for a fresh start
- **Update Based on Actual Reconciliations**: Loops through all invoices and updates payment reconcile amounts based on actual reconciliation data
- **Company-Specific**: Only processes data for the current company
- **Safe Operation**: Includes logging and error handling
- **User-Friendly Interface**: Accessible through company settings with confirmation dialog

## How It Works

### Step 1: Reset Reconcile Amounts
- Finds all posted payments for the current company
- Resets all `reconcile_amount` fields in `account.payment.invoice` records to 0

### Step 2: Update Based on Actual Reconciliations
- Loops through all posted invoices for the current company
- For each invoice, examines all partial reconciliations
- Identifies payment lines that are reconciled with invoice lines
- Updates or creates `account.payment.invoice` records with correct reconcile amounts

## Usage

1. **Install the Module**: Install `payment_reconcile_fix` module
2. **Access Company**: Go to Settings > Companies > Companies
3. **Open Your Company**: Click on your company record
4. **Find the Button**: Look for the "Fix Payment Reconciliations" button in the top-right button box
5. **Run the Fix**: Click the "Fix Payment Reconciliations" button
6. **Confirm**: Confirm the operation in the dialog
7. **Review Results**: Check the notification for summary of changes made

## Safety Features
- **Company Isolation**: Only processes data for the current company
- **Confirmation Dialog**: Requires user confirmation before execution
- **Comprehensive Logging**: Logs all operations for debugging
- **Error Handling**: Graceful error handling with user-friendly messages
- **Progress Tracking**: Shows progress for large datasets

## Technical Details
- **Dependencies**: Requires `account`, `auto_reconcile_payment`, and `base` modules
- **Models Extended**: `res.company`
- **Security**: Restricted to Account Manager group
- **Performance**: Processes records in batches with progress logging

## Backup Recommendation
**Important**: Always backup your database before running this fix, as it modifies existing reconciliation data.

## Support
This module is designed to work with Odoo 17 and the `auto_reconcile_payment` module. For issues or customizations, contact your system administrator.
