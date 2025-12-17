from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare
import logging

_logger = logging.getLogger(__name__)
# float_compare return :
#  0 if the numbers are equal 
# -1 if the first float number is less than the second
#  1 if the first float number is greater than the second

class AccountPaymentInvoices(models.Model):
    _name = 'account.payment.invoice'

    invoice_id = fields.Many2one('account.move', string='Invoice')
    payment_id = fields.Many2one('account.payment', string='Payment')
    currency_id = fields.Many2one(related='invoice_id.currency_id')
    origin = fields.Char(related='invoice_id.invoice_origin')
    date_invoice = fields.Date(related='invoice_id.invoice_date')
    date_due = fields.Date(related='invoice_id.invoice_date_due')
    payment_state = fields.Selection(related='payment_id.state', store=True)
    reconcile_amount = fields.Monetary(string='Reconcile Amount')
    amount_total = fields.Monetary(related="invoice_id.amount_total")
    residual = fields.Monetary(related="invoice_id.amount_residual")

    def unlink(self):
        # Store the payment_ids before deletion to update them after unlink
        payment_ids = self.mapped('payment_id')
        result = super(AccountPaymentInvoices, self).unlink()
        # Update reconcile amounts for all affected payments
        for payment in payment_ids:
            if payment.exists():
                payment._update_reconcile_amount()
        return result

    def get_reconcile_lines(self):
        map_fields = { 'inbound': 'credit', 'outbound': 'debit' }
        field_name = map_fields[self.payment_id.payment_type]
        return self.payment_id.move_id.line_ids.filtered(lambda line: line[field_name] > 0)

    def do_reconcile_lines(self):
        for rec in self:
            if not rec.reconcile_amount: continue
            lines = self.get_reconcile_lines()
            lines += rec.invoice_id.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
            precision_digits = rec.currency_id.decimal_places or 2
            if float_compare(rec.amount_total, rec.reconcile_amount, precision_digits=precision_digits) != 1:
                lines = lines.with_context(amount=rec.reconcile_amount)
            lines.reconcile()


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def js_assign_outstanding_line(self, line_id):
        ''' Override to add the invoice to the payment's invoices section when a payment is applied to an invoice '''
        # Call the original method to perform the reconciliation
        result = super(AccountMove, self).js_assign_outstanding_line(line_id)
        
        # Get the payment line that was just reconciled
        payment_line = self.env['account.move.line'].browse(line_id)
        
        # Check if this line is from a payment
        if payment_line.payment_id and self.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
            payment = payment_line.payment_id
            
            # Check if this invoice is already in the payment's invoices
            existing_invoice = payment.payment_invoice_ids.filtered(lambda x: x.invoice_id.id == self.id)
            _logger.info("Existing invoice: %s", existing_invoice)
            _logger.info("******************************************")
            
            # Determine the reconciled amount
            if payment.payment_type == 'inbound':
                reconcile_amount = payment_line.credit
            else:
                reconcile_amount = payment_line.debit
                
            # If payment is posted, update or create the invoice record
            if payment.state in ['in_process', 'paid']:
                _logger.info("Payment state: %s", payment.state)
                _logger.info("******************************************")
                
                if existing_invoice:
                    # Update existing record
                    _logger.info("Updating existing invoice record")
                    existing_invoice.write({
                        'reconcile_amount': existing_invoice.reconcile_amount + reconcile_amount
                    })
                else:
                    # Create a new payment invoice record
                    _logger.info("Creating new invoice record")
                    self.env['account.payment.invoice'].create({
                        'invoice_id': self.id,
                        'payment_id': payment.id,
                        'reconcile_amount': reconcile_amount
                    })
                
        return result
        
    def js_remove_outstanding_partial(self, partial_id):
        ''' Override to set reconcile_amount to zero in the invoice list when unreconciling '''
        
        # Get the partial reconciliation before unlinking it
        partial = self.env['account.partial.reconcile'].browse(partial_id)
        _logger.info("Partial record: %s, amount: %s", partial, partial.amount)
        
        # Find the payment line involved in this reconciliation
        debit_line = partial.debit_move_id
        credit_line = partial.credit_move_id
        
        # Determine which line is from the payment
        payment_line = False
        if debit_line.payment_id:
            payment_line = debit_line
        elif credit_line.payment_id:
            payment_line = credit_line
        else:
            _logger.info("No payment line found")
            
        # If we found a payment line, update the invoice in the payment's invoices
        if payment_line and payment_line.payment_id:
            payment = payment_line.payment_id
            
            # First try to find the invoice by ID
            invoice_move = (
                    partial.debit_move_id.move_id
                    if partial.debit_move_id.move_id.move_type in ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')
                    else partial.credit_move_id.move_id
                )
            invoice_line = payment.payment_invoice_ids.filtered(lambda x: x.invoice_id.id == invoice_move.id)
            _logger.info("Invoice line111: %s", invoice_line)
            
            # If not found by ID, try to find by name (reference number)
            if not invoice_line:
                _logger.info("Invoice not found by ID, trying to find by name")
                _logger.info("Invoice name: %s", self.name)
                # _logger.info("Payment invoice ids: %s", payment.payment_invoice_ids[0].invoice_id.name)
                invoice_line = payment.payment_invoice_ids.filtered(lambda x: x.invoice_id.name == invoice_move.name)
                _logger.info("Invoice line222: %s", invoice_line)
            
            # If still not found, try to find any invoice with matching amount
            if not invoice_line and partial.amount > 0:
                invoice_line = payment.payment_invoice_ids.filtered(lambda x: float_compare(x.reconcile_amount, partial.amount, precision_digits=2) == 0)
                _logger.info("Invoice line333: %s", invoice_line)
                
            if invoice_line:
                invoice_line.write({
                    'reconcile_amount': 0
                })
            else:
                _logger.info("No matching invoice found in payment_invoice_ids for invoice: %s (ID: %s)", self.name, self.id)
            
        # Call the original method to perform the unreconciliation
        return super(AccountMove, self).js_remove_outstanding_partial(partial_id)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    invoice_id = fields.Many2one('account.move', string='Invoice')

    def _create_reconciliation_partials(self):
        '''create the partial reconciliation between all the records in self
         :return: A recordset of account.partial.reconcile.
        '''
        partials_vals_list, exchange_data = self._prepare_reconciliation_partials([
            {
                'record': line,
                'balance': line.balance,
                'amount_currency': line.amount_currency,
                'amount_residual': line.amount_residual,
                'amount_residual_currency': line.amount_residual_currency,
                'company': line.company_id,
                'currency': line.currency_id,
                'date': line.date,
            }
            for line in self
        ])
        partial_amount = self.env.context.get('amount', False)
        if partial_amount:
            partials_vals_list[0].update({
                'amount': partial_amount, 
                'debit_amount_currency': partial_amount, 
                'credit_amount_currency': partial_amount,
            })

        partials = self.env['account.partial.reconcile'].create(partials_vals_list)

        # ==== Create exchange difference moves ====
        for index, exchange_vals in exchange_data.items():
            partials[index].exchange_move_id = self._create_exchange_difference_move(exchange_vals)

        return partials


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_invoice_ids = fields.One2many('account.payment.invoice', 'payment_id',string="Customer Invoices",invisible=True)
    
    paerner_currency_id = fields.Many2one('res.currency', related='partner_id.currency_id')
    partner_credit = fields.Monetary(related='partner_id.credit', currency_field='paerner_currency_id')
    paerner_debit = fields.Monetary(related='partner_id.debit', currency_field='paerner_currency_id')

    reconcile_payment = fields.Selection([
        ('invoice_payment', 'Invoice Reconcile Payment'),
        ('down_payment', 'Down Payment'),
    ], required=True, default='invoice_payment')

    def amount_to_words(self):
        return self.currency_id.amount_to_text(self.amount)
    
    def _get_en_payment_type_map(self):
        return {
            'customer-inbound': 'Receipt',
            'customer-outbound': 'Refund',
            'supplier-outbound': 'Payment',
            'supplier-inbound': 'Refund',
        }
    
    def _get_ar_payment_type_map(self):
        return {
            'customer-inbound': 'قبض',
            'customer-outbound': 'استرداد',
            'supplier-outbound': 'صرف',
            'supplier-inbound': 'استرداد',
        }
    
    def _get_en_partner_type_map(self):
        return {
            'customer': 'Customer',
            'supplier': 'Vendor',
        }
    
    def _get_ar_partner_type_map(self):
        return {
            'customer': 'العملاء',
            'supplier': 'الموردين',
        }
    
    def account_payment_report_en_title(self):
        key = '%s-%s' % (self.partner_type, self.payment_type)
        en_title = '{partner_type} Voucher ({payment_type})'
        return en_title.format(
            partner_type = self._get_en_partner_type_map()[self.partner_type],
            payment_type = self._get_en_payment_type_map()[key],
        )
    
    def account_payment_report_ar_title(self):
        key = '%s-%s' % (self.partner_type, self.payment_type)
        ar_title = 'سندات {partner_type} ({payment_type})'
        return ar_title.format(
            partner_type = self._get_ar_partner_type_map()[self.partner_type],
            payment_type = self._get_ar_payment_type_map()[key],
        )
    
    def cxxx(self):
        self.partner_type

        if self.partner_type == 'customer' and self.payment_type == 'inbound':
            return _('Customer Voucher (Receipt)')
        elif self.partner_type == 'customer' and self.payment_type == 'outbound':
            return _('Customer Voucher (Refund)')
        elif self.partner_type == 'supplier' and self.payment_type == 'outbound':
            return _('Vendor Voucher (Payment)')
        elif self.partner_type == 'supplier' and self.payment_type == 'inbound':
            return _('Vendor Voucher (Refund)')
        return self.currency_id.amount_to_text(self.amount)

    @api.onchange('payment_type', 'partner_type', 'partner_id', 'currency_id')
    def _onchange_to_get_vendor_invoices(self):
        if self.payment_type in ['inbound', 'outbound'] and self.partner_type and self.partner_id and self.currency_id:
            self.payment_invoice_ids = [(6, 0, [])]
            if self.payment_type == 'inbound' and self.partner_type == 'customer':
                invoice_type = 'out_invoice'
            elif self.payment_type == 'outbound' and self.partner_type == 'customer':
                invoice_type = 'out_refund'
            elif self.payment_type == 'outbound' and self.partner_type == 'supplier':
                invoice_type = 'in_invoice'
            else:
                invoice_type = 'in_refund'
            invoice_recs = self.env['account.move'].search([
                ('partner_id', 'child_of', self.partner_id.id), 
                ('state', '=', 'posted'), 
                ('move_type', '=', invoice_type), 
                ('payment_state', '!=', 'paid'), 
                ('currency_id', '=', self.currency_id.id)],order='invoice_date')
            payment_invoice_values = []
            for invoice_rec in invoice_recs:
                payment_invoice_values.append([0, 0, {'invoice_id': invoice_rec.id}])
            self.payment_invoice_ids = payment_invoice_values
            self._update_reconcile_amount()

    def _update_reconcile_amount(self):
        # First set all reconcile_amount to 0
        for line in self.payment_invoice_ids:
            line.reconcile_amount = 0
            
        # Then distribute the amount
        amount = self.amount
        for line in self.payment_invoice_ids:
            if line.residual <= amount:
                line.reconcile_amount = line.residual
                amount -= line.residual
            else:
                line.reconcile_amount = amount 
                break
        
    @api.onchange('amount')
    def _onchange_amount(self):
        self._update_reconcile_amount()
    
    def refresh_invoices(self):
        """Public method to refresh the list of invoices"""
        for rec in self:
            rec._onchange_to_get_vendor_invoices()
        return True

    def action_post(self):
        super(AccountPayment, self).action_post()
        for payment in self:
            if payment.reconcile_payment != 'invoice_payment':
                continue
            
            # Delete records with zero reconcile amount
            zero_amount_records = payment.payment_invoice_ids.filtered(lambda x: x.reconcile_amount == 0.0)
            if zero_amount_records:
                _logger.info("Deleting %d payment invoice records with zero reconcile amount for payment %s", 
                           len(zero_amount_records), payment.name)
                zero_amount_records.unlink()
            
            if payment._check_reconcile_amount():
                raise UserError(_("The sum of the reconcile amount of listed invoices are greater than payment's amount."))
            payment.payment_invoice_ids.do_reconcile_lines()
        return True

    def _check_reconcile_amount(self):
        if self.payment_invoice_ids:
            total_reconcile = sum(self.payment_invoice_ids.mapped('reconcile_amount'))
            # Compare the rounded payment amount with the rounded total reconcile amount
            # using float_compare, where -1 indicates payment amount is less than total reconcile amount.
            # Use precision_digits instead of rounding value
            precision_digits = self.currency_id.decimal_places or 2
            return float_compare(self.amount, total_reconcile, precision_digits=precision_digits) == -1
