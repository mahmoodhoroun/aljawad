from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero
import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    def action_auto_reconcile_oldest(self):
        """
        Automatically reconcile unpaid invoices with unreconciled payments based on age.
        Process:
        1. Find unpaid invoices ordered by date (oldest first)
        2. Find payments with unreconciled amounts ordered by date (oldest first)
        3. Reconcile oldest invoices with oldest payments
        4. Continue until all invoices are paid or all payments are fully reconciled
        """
        try:
            company_id = self.id
            
            # Ensure we're working with the correct company context
            self = self.with_company(company_id)
            self.env.context = dict(self.env.context, allowed_company_ids=[company_id])
            
            _logger.info("Starting automatic reconciliation for company: %s", self.name)
            
            # Step 1: Get unpaid invoices ordered by date (oldest first)
            invoices = self.env['account.move'].sudo().search([
                ('company_id', '=', company_id),
                ('move_type', 'in', ['out_invoice']),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('amount_residual', '!=', 0)
            ], order='invoice_date asc, id asc')
            
            if not invoices:
                _logger.info("No unpaid invoices found for company %s", self.name)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Action Needed'),
                        'message': _('No unpaid invoices found for reconciliation.'),
                        'type': 'info',
                        'sticky': False,
                    }
                }
            
            _logger.info("Found %d unpaid invoices to process", len(invoices))
            
            # Step 2: Get outstanding payment lines using the same logic as invoice outstanding widget
            # This will find all unreconciled payment lines, journal entries, and other credit/debit entries
            
            # Get all receivable accounts for the company
            receivable_accounts = self.env['account.account'].sudo().search([
                # ('company_id', '=', company_id),
                ('account_type', '=', 'asset_receivable')
            ])
            
            if not receivable_accounts:
                _logger.info("No receivable accounts found for company %s", self.name)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Action Needed'),
                        'message': _('No receivable accounts found.'),
                        'type': 'info',
                        'sticky': False,
                    }
                }
            
            # Search for outstanding credit lines (payments, credit notes, etc.)
            domain = [
                ('account_id', 'in', receivable_accounts.ids),
                ('parent_state', '=', 'posted'),
                ('reconciled', '=', False),
                ('balance', '<', 0.0),  # Credit balance for receivables
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]
            
            outstanding_lines = self.env['account.move.line'].sudo().search(domain, order='date asc, id asc')
            
            if not outstanding_lines:
                _logger.info("No outstanding credit lines found for company %s", self.name)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Action Needed'),
                        'message': _('No outstanding credit lines found for reconciliation.'),
                        'type': 'info',
                        'sticky': False,
                    }
                }
            
            _logger.info("Found %d outstanding credit lines to process", len(outstanding_lines))
            
            # Prepare outstanding lines data with amounts
            outstanding_lines_data = []
            for line in outstanding_lines:
                # Calculate available amount (same logic as outstanding widget)
                if line.currency_id and line.currency_id != line.company_currency_id:
                    # Foreign currency line
                    amount = abs(line.amount_residual_currency)
                    currency = line.currency_id
                else:
                    # Company currency line
                    amount = abs(line.amount_residual)
                    currency = line.company_currency_id
                if line.move_id.show_in_outstanding:
                    if not currency.is_zero(amount):
                        outstanding_lines_data.append({
                            'line': line,
                            'amount': amount,
                            'currency': currency,
                            'partner_id': line.partner_id.id,
                            'payment_id': line.payment_id.id if line.payment_id else False,
                        })
                    
            if not outstanding_lines_data:
                _logger.info("No outstanding lines with available amounts found")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Action Needed'),
                        'message': _('No outstanding lines with available amounts found.'),
                        'type': 'info',
                        'sticky': False,
                    }
                }
            
            _logger.info("Found %d outstanding lines with available amounts", len(outstanding_lines_data))
            
            # Step 3: Reconcile oldest invoices with oldest outstanding lines
            invoices_reconciled = 0
            lines_reconciled = 0
            total_reconciled_amount = 0
            
            # Process each invoice
            for invoice in invoices:
                if not outstanding_lines_data:
                    break  # No more outstanding lines with available amounts
                
                # Skip if invoice is fully paid
                if float_is_zero(invoice.amount_residual, precision_rounding=invoice.currency_id.rounding):
                    continue
                
                invoice_residual = invoice.amount_residual
                invoice_fully_reconciled = False
                
                # Get all outstanding lines for this invoice's partner
                partner_lines = [l for l in outstanding_lines_data if l['partner_id'] == invoice.partner_id.id]
                
                # Try to reconcile with all available partner outstanding lines
                while invoice_residual > 0 and partner_lines and not invoice_fully_reconciled:
                    line_data = partner_lines[0]  # Get oldest outstanding line
                    outstanding_line = line_data['line']
                    available_amount = line_data['amount']
                    line_currency = line_data['currency']
                    
                    # Skip if line and invoice are incompatible for other reasons
                    if outstanding_line.partner_id.id != invoice.partner_id.id:
                        # This should never happen now with our filtered list, but keep as safety
                        partner_lines.pop(0)
                        # Also remove from main list if needed
                        if line_data in outstanding_lines_data:
                            outstanding_lines_data.remove(line_data)
                        if not partner_lines:
                            break
                        continue
                    
                    # Convert amount to invoice currency if needed
                    if line_currency != invoice.currency_id:
                        available_amount_in_invoice_currency = line_currency._convert(
                            available_amount,
                            invoice.currency_id,
                            invoice.company_id,
                            outstanding_line.date,
                        )
                    else:
                        available_amount_in_invoice_currency = available_amount
                    
                    # Determine amount to reconcile
                    amount_to_reconcile = min(invoice_residual, available_amount_in_invoice_currency)
                    
                    try:
                        # Handle payment invoice records only if this outstanding line is from a payment
                        payment_id = line_data.get('payment_id')
                        if payment_id:
                            payment = self.env['account.payment'].sudo().browse(payment_id)
                            existing_invoice = payment.payment_invoice_ids.filtered(
                                lambda x: x.invoice_id.id == invoice.id
                            )
                            
                            try:
                                if existing_invoice:
                                    # Update existing record
                                    new_amount = existing_invoice.reconcile_amount + amount_to_reconcile
                                    existing_invoice.write({'reconcile_amount': new_amount})
                                    _logger.info("Updated payment %s for invoice %s: +%s (total: %s)", 
                                                payment.name, invoice.name, amount_to_reconcile, new_amount)
                                else:
                                    # Create new payment invoice record
                                    self.env['account.payment.invoice'].sudo().create({
                                        'invoice_id': invoice.id,
                                        'payment_id': payment.id,
                                        'reconcile_amount': amount_to_reconcile
                                    })
                                    _logger.info("Created new payment invoice record for payment %s and invoice %s: %s", 
                                                payment.name, invoice.name, amount_to_reconcile)
                            except Exception as e:
                                _logger.error("Error updating payment invoice record: %s", str(e))
                        else:
                            _logger.info("Reconciling non-payment line %s with invoice %s: %s", 
                                        outstanding_line.move_id.name, invoice.name, amount_to_reconcile)
                        
                        # Update tracking variables
                        invoice_residual -= amount_to_reconcile
                        
                        # Convert back to line currency for tracking
                        if line_currency != invoice.currency_id:
                            amount_in_line_currency = invoice.currency_id._convert(
                                amount_to_reconcile,
                                line_currency,
                                invoice.company_id,
                                outstanding_line.date,
                            )
                        else:
                            amount_in_line_currency = amount_to_reconcile
                            
                        line_data['amount'] -= amount_in_line_currency
                        total_reconciled_amount += amount_to_reconcile
                        
                        # Check if invoice is now fully reconciled
                        if float_is_zero(invoice_residual, precision_rounding=invoice.currency_id.rounding):
                            invoice_fully_reconciled = True
                            invoices_reconciled += 1
                            _logger.info("Invoice %s fully reconciled", invoice.name)
                        
                        # Check if outstanding line is now fully used
                        if line_currency.is_zero(line_data['amount']):
                            lines_reconciled += 1
                            # Remove from both lists
                            if line_data in partner_lines:
                                partner_lines.remove(line_data)
                            if line_data in outstanding_lines_data:
                                outstanding_lines_data.remove(line_data)
                            _logger.info("Outstanding line %s fully reconciled", outstanding_line.move_id.name)
                        
                        # Perform actual reconciliation
                        # Get the invoice lines with the same account as the outstanding line
                        invoice_lines = invoice.line_ids.filtered(
                            lambda line: line.account_id == outstanding_line.account_id and not line.reconciled
                        )
                        
                        if outstanding_line and invoice_lines:
                            # Reconcile the lines
                            (outstanding_line + invoice_lines).reconcile()
                            _logger.info("Reconciled outstanding line %s with invoice lines", outstanding_line.move_id.name)
                            
                    except Exception as e:
                        _logger.error("Error reconciling outstanding line %s with invoice %s: %s", 
                                    outstanding_line.move_id.name, invoice.name, str(e))
                        # Move to next outstanding line if there was an error with this one
                        if line_data in partner_lines:
                            partner_lines.remove(line_data)
                        if line_data in outstanding_lines_data:
                            outstanding_lines_data.remove(line_data)
                        if not outstanding_lines_data:
                            break
            
            # Commit the changes
            self.env.cr.commit()
            
            # Calculate original counts for summary
            original_invoices_count = len(invoices)
            original_lines_count = len([line for line in outstanding_lines_data]) + lines_reconciled
            
            message = _(
                "Automatic reconciliation completed successfully!\n\n"
                "Summary:\n"
                "- Processed %d unpaid invoices\n"
                "- Processed %d outstanding credit lines\n"
                "- Fully reconciled %d invoices\n"
                "- Fully reconciled %d outstanding lines\n"
                "- Total reconciled amount: %s"
            ) % (original_invoices_count, original_lines_count, invoices_reconciled, lines_reconciled, total_reconciled_amount)
            
            _logger.info(message)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': message,
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error("Error during automatic reconciliation: %s", str(e))
            raise UserError(_("An error occurred during automatic reconciliation: %s") % str(e))

    def action_auto_reconcile_reversals(self):
        """
        Automatically reconcile invoices with their reversal entries.
        Process:
        1. Find all invoices in the company
        2. For each invoice, check if it has a reversal entry
        3. If both invoice and reversal are unreconciled, reconcile them
        """
        try:
            company_id = self.id
            
            # Ensure we're working with the correct company context
            self = self.with_company(company_id)
            self.env.context = dict(self.env.context, allowed_company_ids=[company_id])
            
            _logger.info("Starting automatic reversal reconciliation for company: %s", self.name)
            
            # Step 1: Get all invoices in the company
            invoices = self.env['account.move'].sudo().search([
                ('company_id', '=', company_id),
                ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
                ('state', '=', 'posted'),
                ('reversed_entry_id', '!=', False)  # Only invoices that have been reversed
            ], order='date asc, id asc')
            
            if not invoices:
                _logger.info("No reversed invoices found for company %s", self.name)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Action Needed'),
                        'message': _('No reversed invoices found for reconciliation.'),
                        'type': 'info',
                        'sticky': False,
                    }
                }
            
            _logger.info("Found %d reversed invoices to process", len(invoices))
            
            # Step 2: Process each invoice and its reversal
            reconciled_pairs = 0
            total_reconciled_amount = 0
            errors = []
            
            for invoice in invoices:
                try:
                    # Get the reversal entry
                    reversal = invoice.reversed_entry_id
                    
                    if not reversal:
                        continue
                    
                    # Check if both invoice and reversal are posted
                    if invoice.state != 'posted' or reversal.state != 'posted':
                        _logger.info("Skipping invoice %s - not both posted (invoice: %s, reversal: %s)", 
                                   invoice.name, invoice.state, reversal.state)
                        continue
                    
                    # Get receivable/payable lines for both moves
                    invoice_lines = invoice.line_ids.filtered(
                        lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable') 
                        and not line.reconciled
                    )
                    
                    reversal_lines = reversal.line_ids.filtered(
                        lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable') 
                        and not line.reconciled
                        and line.account_id == invoice_lines[0].account_id if invoice_lines else False
                    )
                    
                    if not invoice_lines or not reversal_lines:
                        _logger.info("Skipping invoice %s - no unreconciled receivable/payable lines found", invoice.name)
                        continue
                    
                    # Check if lines have opposite balances (one debit, one credit)
                    invoice_balance = sum(invoice_lines.mapped('balance'))
                    reversal_balance = sum(reversal_lines.mapped('balance'))
                    
                    if (invoice_balance > 0 and reversal_balance > 0) or (invoice_balance < 0 and reversal_balance < 0):
                        _logger.info("Skipping invoice %s - balances don't oppose each other (invoice: %s, reversal: %s)", 
                                   invoice.name, invoice_balance, reversal_balance)
                        continue
                    
                    # Check if amounts match (allowing for small rounding differences)
                    if not float_is_zero(abs(invoice_balance) - abs(reversal_balance), 
                                       precision_rounding=invoice.currency_id.rounding):
                        _logger.info("Skipping invoice %s - amounts don't match (invoice: %s, reversal: %s)", 
                                   invoice.name, abs(invoice_balance), abs(reversal_balance))
                        continue
                    
                    # Perform reconciliation
                    lines_to_reconcile = invoice_lines + reversal_lines
                    lines_to_reconcile.reconcile()
                    
                    reconciled_pairs += 1
                    total_reconciled_amount += abs(invoice_balance)
                    
                    _logger.info("Successfully reconciled invoice %s with reversal %s (amount: %s)", 
                               invoice.name, reversal.name, abs(invoice_balance))
                    
                except Exception as e:
                    error_msg = "Error reconciling invoice %s with reversal: %s" % (invoice.name, str(e))
                    _logger.error(error_msg)
                    errors.append(error_msg)
                    continue
            
            # Commit the changes
            self.env.cr.commit()
            
            # Prepare result message
            if errors:
                error_summary = "\n".join(errors[:5])  # Show first 5 errors
                if len(errors) > 5:
                    error_summary += f"\n... and {len(errors) - 5} more errors"
                
                message = _(
                    "Reversal reconciliation completed with some errors!\n\n"
                    "Summary:\n"
                    "- Processed %d reversed invoices\n"
                    "- Successfully reconciled %d invoice-reversal pairs\n"
                    "- Total reconciled amount: %s\n"
                    "- Errors encountered: %d\n\n"
                    "First few errors:\n%s"
                ) % (len(invoices), reconciled_pairs, total_reconciled_amount, len(errors), error_summary)
                
                notification_type = 'warning'
            else:
                message = _(
                    "Reversal reconciliation completed successfully!\n\n"
                    "Summary:\n"
                    "- Processed %d reversed invoices\n"
                    "- Successfully reconciled %d invoice-reversal pairs\n"
                    "- Total reconciled amount: %s"
                ) % (len(invoices), reconciled_pairs, total_reconciled_amount)
                
                notification_type = 'success'
            
            _logger.info(message)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Reversal Reconciliation Complete'),
                    'message': message,
                    'type': notification_type,
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error("Error during reversal reconciliation: %s", str(e))
            raise UserError(_("An error occurred during reversal reconciliation: %s") % str(e))

    def action_fix_payment_reconcile(self):
        """
        Fix payment reconcile amounts by:
        1. Reset all payment reconcile amounts to 0
        2. Loop through all invoices and update payment reconcile amounts based on actual reconciliations
        """
        try:
            company_id = self.id
            
            # Ensure we're working with the correct company context
            self = self.with_company(company_id)
            self.env.context = dict(self.env.context, allowed_company_ids=[company_id])
            
            # Step 1: Reset all payment reconcile amounts to 0 for current company
            _logger.info("Starting payment reconcile fix for company: %s", self.name)
            
            # Get all payments for current company
            payments = self.env['account.payment'].sudo().search([
                ('company_id', '=', company_id),
                ('state', 'in', ['in_process', 'paid'])
            ])
            
            _logger.info("Found %d payments to process", len(payments))
            
            # Reset all reconcile amounts to 0
            payment_invoices = self.env['account.payment.invoice'].sudo().search([
                ('payment_id', 'in', payments.ids)
            ])
            
            _logger.info("Resetting reconcile amounts for %d payment invoice records", len(payment_invoices))
            payment_invoices.write({'reconcile_amount': 0.0})
            
            # Step 2: Loop through all invoices and update payment reconcile amounts
            invoices = self.env['account.move'].sudo().search([
                ('company_id', '=', company_id),
                ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
                ('state', '=', 'posted')
            ])
            
            _logger.info("Processing %d invoices", len(invoices))
            
            processed_count = 0
            updated_count = 0
            created_count = 0
            
            for invoice in invoices:
                processed_count += 1
                
                if processed_count % 100 == 0:
                    _logger.info("Processed %d/%d invoices", processed_count, len(invoices))
                
                # Get all reconciled payment lines for this invoice
                # Filter lines that belong to the current company only
                invoice_lines = invoice.line_ids.filtered(
                    lambda line: line.account_id.account_type in ['asset_receivable', 'liability_payable'] and 
                                line.company_id.id == company_id
                )
                
                for invoice_line in invoice_lines:
                    # Get all partial reconciliations for this line
                    for partial in invoice_line.matched_debit_ids + invoice_line.matched_credit_ids:
                        # Determine which line is the payment line
                        if partial.debit_move_id == invoice_line:
                            payment_line = partial.credit_move_id
                            reconcile_amount = partial.amount
                        else:
                            payment_line = partial.debit_move_id
                            reconcile_amount = partial.amount
                        
                        # Check if this line belongs to a payment and is from the same company
                        if payment_line.payment_id and payment_line.company_id.id == company_id:
                            payment = payment_line.payment_id
                            
                            # Check if this invoice is already in the payment's invoices
                            existing_invoice = payment.payment_invoice_ids.filtered(
                                lambda x: x.invoice_id.id == invoice.id
                            )
                            _logger.info("Existing invoice: %s", existing_invoice)
                            
                            if existing_invoice:
                                # If there are multiple records (shouldn't happen), keep only the first one
                                if len(existing_invoice) > 1:
                                    _logger.warning("Found multiple payment invoice records for payment %s and invoice %s. Cleaning up duplicates.", 
                                                  payment.name, invoice.name)
                                    # Delete duplicates, keep the first one
                                    duplicates = existing_invoice[1:]
                                    duplicates.unlink()
                                    existing_invoice = existing_invoice[0]
                                else:
                                    existing_invoice = existing_invoice[0]
                                    _logger.info("Existing invoice123123: %s", existing_invoice)
                                
                                # Update existing record - add to current reconcile amount
                                new_amount = existing_invoice.reconcile_amount + reconcile_amount
                                existing_invoice.write({'reconcile_amount': new_amount})
                                updated_count += 1
                                _logger.debug("Updated payment %s for invoice %s: %s", 
                                            payment.name, invoice.name, reconcile_amount)
                            else:
                                # Create new payment invoice record
                                self.env['account.payment.invoice'].sudo().create({
                                    'invoice_id': invoice.id,
                                    'payment_id': payment.id,
                                    'reconcile_amount': reconcile_amount
                                })
                                created_count += 1
                                _logger.debug("Created new payment invoice record for payment %s and invoice %s: %s", 
                                            payment.name, invoice.name, reconcile_amount)
            
            # Commit the changes
            self.env.cr.commit()
            
            message = _(
                "Payment reconcile fix completed successfully!\n\n"
                "Summary:\n"
                "- Processed %d payments\n"
                "- Reset %d payment invoice records\n"
                "- Processed %d invoices\n"
                "- Updated %d existing payment invoice records\n"
                "- Created %d new payment invoice records"
            ) % (len(payments), len(payment_invoices), len(invoices), updated_count, created_count)
            
            _logger.info(message)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': message,
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error("Error during payment reconcile fix: %s", str(e))
            raise UserError(_("An error occurred while fixing payment reconciliations: %s") % str(e))
    
    def action_cleanup_zero_reconcile_amounts(self):
        """
        Clean up payment invoice records with zero reconcile amounts for all payments in this company
        """
        try:
            company_id = self.id
            
            # Ensure we're working with the correct company context
            self = self.with_company(company_id)
            self.env.context = dict(self.env.context, allowed_company_ids=[company_id])
            
            _logger.info("Starting cleanup of zero reconcile amounts for company: %s", self.name)
            
            # Get all payments for current company
            payments = self.env['account.payment'].sudo().search([
                ('company_id', '=', company_id)
            ])
            
            _logger.info("Found %d payments to check", len(payments))
            
            total_deleted = 0
            processed_payments = 0
            
            for payment in payments:
                processed_payments += 1
                
                if processed_payments % 50 == 0:
                    _logger.info("Processed %d/%d payments", processed_payments, len(payments))
                
                # Find records with zero reconcile amount for this payment
                # Use float_compare to handle floating point precision issues
                zero_amount_records = payment.payment_invoice_ids.filtered(
                    lambda x: float_compare(x.reconcile_amount, 0.0, precision_digits=2) == 0
                )
                
                if zero_amount_records:
                    deleted_count = len(zero_amount_records)
                    total_deleted += deleted_count
                    
                    # Log details of what we're deleting
                    for record in zero_amount_records:
                        _logger.info("Deleting payment invoice record: Payment %s, Invoice %s, Amount: %s", 
                                   record.payment_id.name, record.invoice_id.name, record.reconcile_amount)
                    
                    # Store payment IDs to avoid automatic reconcile amount update
                    payment_ids_to_skip = zero_amount_records.mapped('payment_id')
                    
                    # Delete records without triggering _update_reconcile_amount
                    # Use SQL delete to bypass the unlink method that triggers recalculation
                    record_ids = zero_amount_records.ids
                    if record_ids:
                        self.env.cr.execute(
                            "DELETE FROM account_payment_invoice WHERE id IN %s",
                            (tuple(record_ids),)
                        )
            
            # Commit the changes
            self.env.cr.commit()
            
            message = _(
                "Zero reconcile amounts cleanup completed successfully!\n\n"
                "Summary:\n"
                "- Processed %d payments\n"
                "- Deleted %d payment invoice records with zero reconcile amounts"
            ) % (len(payments), total_deleted)
            
            _logger.info(message)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': message,
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error("Error during zero reconcile amounts cleanup: %s", str(e))
            raise UserError(_("An error occurred while cleaning up zero reconcile amounts: %s") % str(e))
    
    def action_preview_zero_reconcile_cleanup(self):
        """
        Preview what records would be deleted by the zero reconcile amounts cleanup
        """
        try:
            company_id = self.id
            
            # Ensure we're working with the correct company context
            self = self.with_company(company_id)
            self.env.context = dict(self.env.context, allowed_company_ids=[company_id])
            
            _logger.info("Previewing zero reconcile amounts cleanup for company: %s", self.name)
            
            # Get all payments for current company
            payments = self.env['account.payment'].sudo().search([
                ('company_id', '=', company_id)
            ])
            
            preview_records = []
            total_to_delete = 0
            
            for payment in payments:
                # Find records with zero reconcile amount for this payment
                zero_amount_records = payment.payment_invoice_ids.filtered(
                    lambda x: float_compare(x.reconcile_amount, 0.0, precision_digits=2) == 0
                )
                
                if zero_amount_records:
                    for record in zero_amount_records:
                        preview_records.append({
                            'payment': record.payment_id.name,
                            'invoice': record.invoice_id.name,
                            'amount': record.reconcile_amount,
                            'currency': record.currency_id.name
                        })
                        total_to_delete += 1
            
            # Create preview message
            if total_to_delete == 0:
                message = _("No records with zero reconcile amounts found.")
            else:
                preview_text = "\n".join([
                    f"- Payment: {r['payment']}, Invoice: {r['invoice']}, Amount: {r['amount']} {r['currency']}"
                    for r in preview_records[:10]  # Show first 10 records
                ])
                
                if total_to_delete > 10:
                    preview_text += f"\n... and {total_to_delete - 10} more records"
                
                message = _(
                    "Preview: Found %d records with zero reconcile amounts that would be deleted:\n\n%s"
                ) % (total_to_delete, preview_text)
            
            _logger.info("Preview completed: %d records would be deleted", total_to_delete)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Preview Results'),
                    'message': message,
                    'type': 'info',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error("Error during preview: %s", str(e))
            raise UserError(_("An error occurred during preview: %s") % str(e))

