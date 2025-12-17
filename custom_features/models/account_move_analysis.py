from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # Fields for workflow type analysis
    is_cash_invoice = fields.Boolean(
        string='Is Cash Invoice',
        compute='_compute_workflow_type',
        store=True,
        help='True if this invoice is a cash invoice'
    )
    is_credit_invoice = fields.Boolean(
        string='Is Credit Invoice',
        compute='_compute_workflow_type',
        store=True,
        help='True if this invoice is a credit invoice'
    )
    workflow_type = fields.Selection(
        [('cash', 'Cash'), ('credit', 'Credit')],
        string='Workflow Type',
        compute='_compute_workflow_type',
        store=True,
        help='Workflow type based on payment terms (cash or credit)'
    )
    
    # Commission fields for analysis
    cash_commission_value = fields.Float(
        string='Cash Commission Value',
        compute='_compute_commission_value',
        store=True
    )
    credit_commission_value = fields.Float(
        string='Credit Commission Value',
        compute='_compute_commission_value',
        store=True
    )
    commission_value = fields.Float(
        string='Commission Value',
        compute='_compute_commission_value',
        store=True
    )
    net_sales2 = fields.Float(
        string='Net Sales',
        compute='_compute_net_sales',
        store=True,
        help='Total amount minus commission value'
    )
    net_sales_before_return = fields.Float(
        string='Net Sales Before Return',
        compute='_compute_net_sales',
        store=True,
        help='Total amount minus commission value'
    )
    
    # Return-related fields
    is_return = fields.Boolean(
        string='Is Return',
        compute='_compute_is_return',
        store=True,
        help='True if this is a credit note (return)'
    )
    
    return_amount = fields.Monetary(
        string='Return Amount',
        compute='_compute_return_amount',
        store=True,
        currency_field='currency_id',
        help='Amount for credit notes/returns (negative for regular credit notes)'
    )
    return_cash_amount = fields.Monetary(
        string='Return Cash Amount',
        compute='_compute_return_cash_amount',
        store=True,
        currency_field='currency_id',
        help='Amount for credit notes/returns (negative for regular credit notes)'
    )
    return_credit_amount = fields.Monetary(
        string='Return Credit Amount',
        compute='_compute_return_credit_amount',
        store=True,
        currency_field='currency_id',
        help='Amount for credit notes/returns (negative for regular credit notes)'
    )
    return_count = fields.Integer(
        string='Return Count',
        compute='_compute_return_count',
        store=True,
        help='Count of return invoices (credit notes)'
    )
    
    # Count fields for cash and credit invoices
    cash_count = fields.Integer(
        string='Cash Invoice',
        compute='_compute_invoice_counts',
        store=True,
        help='1 if this is a cash invoice, 0 otherwise'
    )
    
    credit_count = fields.Integer(
        string='Credit Invoice',
        compute='_compute_invoice_counts',
        store=True,
        help='1 if this is a credit invoice, 0 otherwise'
    )
    
    # Amount fields for cash and credit invoices
    cash_amount = fields.Monetary(
        string='Cash Invoice Amount',
        compute='_compute_invoice_amounts',
        store=True,
        currency_field='currency_id',
        help='Total amount for cash invoices'
    )
    
    credit_amount = fields.Monetary(
        string='Credit Invoice Amount',
        compute='_compute_invoice_amounts',
        store=True,
        currency_field='currency_id',
        help='Total amount for credit invoices'
    )
    net_cash_sales = fields.Monetary(
        string='Net Cash Sales',
        compute='_compute_invoice_amounts',
        store=True,
        currency_field='currency_id',
        help='Net cash sales amount'
    )
    net_credit_sales = fields.Monetary(
        string='Net Credit Sales',
        compute='_compute_invoice_amounts',
        store=True,
        currency_field='currency_id',
        help='Net credit sales amount'
    )

    total_sales = fields.Monetary(
        string='Total Sales',
        compute='_compute_invoice_amounts',
        store=True,
        currency_field='currency_id',
        help='Total sales amount'
    )
    
    @api.depends('type')
    def _compute_workflow_type(self):
        for move in self:
            # Use the existing 'type' field from sh_sale_auto_invoice_workflow module
            if hasattr(move, 'type') and move.type:
                move.workflow_type = move.type
                move.is_cash_invoice = move.type == 'cash'
                move.is_credit_invoice = move.type == 'credit'
            else:
                # If type is not set, don't set a default
                move.workflow_type = False  # None/False instead of default
                move.is_cash_invoice = False
                move.is_credit_invoice = False
    
    @api.depends('commission_type', 'commission_rate', 'fixed_amount', 'amount_total', 'amount_untaxed', 'return_amount', 'type')
    def _compute_commission_value(self):
        for move in self:
            if move.move_type == 'out_invoice':
                commission_value = 0.0
                cash_commission_value = 0.0
                credit_commission_value = 0.0
                
                # Use the existing commission fields from commissions_for_customer module
                if hasattr(move, 'commission_type'):
                    if move.commission_type == 'fixed' and hasattr(move, 'fixed_amount'):
                        commission_value = move.fixed_amount or 0.0
                    elif move.commission_type == 'rate' and hasattr(move, 'commission_rate'):
                        commission_value = (move.amount_total * (move.commission_rate or 0.0) / 100)
                    elif move.commission_type == 'rate_before' and hasattr(move, 'commission_rate'):
                        commission_value = (move.amount_untaxed * (move.commission_rate or 0.0) / 100)
                
                # Set cash_commission_value or credit_commission_value based on invoice type
                if hasattr(move, 'type'):
                    if move.type == 'cash':
                        cash_commission_value = commission_value
                    elif move.type == 'credit':
                        credit_commission_value = commission_value
                
                move.commission_value = commission_value
                move.cash_commission_value = cash_commission_value
                move.credit_commission_value = credit_commission_value
    
    @api.depends('move_type')
    def _compute_is_return(self):
        for move in self:
            move.is_return = move.move_type in ('out_refund', 'in_refund')
            
    @api.depends('move_type', 'amount_total')
    def _compute_return_amount(self):
        for move in self:
            # For credit notes (returns), use the amount_total
            # For regular invoices, set to 0
            if move.move_type == 'out_refund':
                move.return_amount = abs(move.amount_total)
            else:
                move.return_amount = 0.0

    @api.depends('type', 'move_type')
    def _compute_invoice_counts(self):
        for move in self:
            # Only count regular invoices (not credit notes/returns)
            if move.move_type == 'out_invoice':
                # Set cash_count to 1 if this is a cash invoice, 0 otherwise
                move.cash_count = 1 if move.type == 'cash' else 0
                # Set credit_count to 1 if this is a credit invoice, 0 otherwise
                move.credit_count = 1 if move.type == 'credit' else 0
            else:
                # For credit notes/returns, don't count them in cash or credit counts
                move.cash_count = 0
                move.credit_count = 0
                
    @api.depends(
        'workflow_type', 'type', 'amount_total', 'move_type',
        'cash_commission_value', 'credit_commission_value',
        'return_cash_amount', 'return_credit_amount'
    )
    def _compute_invoice_amounts(self):
        for move in self:
            # reset
            move.cash_amount = move.credit_amount = move.total_sales = 0.0
            move.net_cash_sales = move.net_credit_sales = 0.0

            # Prefer workflow_type; fall back to type if needed
            wtype = getattr(move, 'workflow_type', False) or getattr(move, 'type', False)

            if move.move_type == 'out_invoice':
                if wtype == 'cash':
                    move.cash_amount = move.amount_total
                    move.net_cash_sales = move.cash_amount - move.cash_commission_value
                elif wtype == 'credit':
                    move.credit_amount = move.amount_total
                    move.net_credit_sales = move.credit_amount - move.credit_commission_value
                move.total_sales = move.amount_total

            elif move.move_type == 'out_refund':
                # Make returns subtract in aggregates
                if wtype == 'cash':
                    # return_cash_amount is abs(amount_total) on refunds → make it negative
                    move.net_cash_sales = -move.return_cash_amount or -abs(move.amount_total)
                elif wtype == 'credit':
                    move.net_credit_sales = -move.return_credit_amount or -abs(move.amount_total)
        

    @api.depends('move_type')
    def _compute_return_count(self):
        for move in self:
            # Set return_count to 1 for credit notes (returns), 0 otherwise
            move.return_count = 1 if move.move_type == 'out_refund' else 0
            
    @api.depends('move_type', 'amount_total', 'type')
    def _compute_return_cash_amount(self):
        for move in self:
            # For credit notes (returns) with cash type, use the amount_total
            # For other types, set to 0
            if move.move_type == 'out_refund' and move.type == 'cash':
                move.return_cash_amount = abs(move.amount_total)
            else:
                move.return_cash_amount = 0.0
                
    @api.depends('move_type', 'amount_total', 'type')
    def _compute_return_credit_amount(self):
        for move in self:
            # For credit notes (returns) with credit type, use the amount_total
            # For other types, set to 0
            if move.move_type == 'out_refund' and move.type == 'credit':
                move.return_credit_amount = abs(move.amount_total)
            else:
                move.return_credit_amount = 0.0
    
    @api.depends('amount_total', 'commission_value', 'return_amount', 'move_type')
    def _compute_net_sales(self):
        for move in self:
            if move.move_type == 'out_invoice':
                move.net_sales_before_return = move.amount_total - move.commission_value
                move.net_sales2 = move.net_sales_before_return - move.return_amount  # return_amount is 0 on invoices
            elif move.move_type == 'out_refund':
                # returns shouldn’t add to net; make them subtract in aggregates
                move.net_sales_before_return = 0.0
                # return_amount is stored as a positive abs(amount_total)
                move.net_sales2 = -move.return_amount
            else:
                move.net_sales_before_return = 0.0
                move.net_sales2 = 0.0
