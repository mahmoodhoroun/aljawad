from odoo import models, fields, api, _
from collections import defaultdict


class StockMove(models.Model):
    _inherit = 'stock.move'

    is_multi_company_transfer = fields.Boolean(string='Multi-Company Transfer', default=False, copy=False)
    source_company_id = fields.Many2one('res.company', string='Source Company', copy=False)
    dest_company_id = fields.Many2one('res.company', string='Destination Company', copy=False)
    
    def _account_entry_move(self, qty, description, svl_id, cost):
        """ Override to handle custom journal entries for multi-company transfers """
        self.ensure_one()
        am_vals = []
        
        # If not a multi-company transfer, use standard behavior
        if not self.is_multi_company_transfer:
            return super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)
            
        # Skip if not storable product or should be excluded from valuation
        if not self.product_id.is_storable or self._should_exclude_for_valuation():
            return am_vals
            
        # Get accounting data
        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
        
        # Get the transfer account
        transfer_account = self.product_id.categ_id.property_stock_transfer_account_categ_id
        if not transfer_account:
            # If transfer account is not set, use standard behavior
            return super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)
            
        # For outgoing move (from source company)
        if self._is_out() and self.source_company_id:
            cost_outgoing = -1 * cost
            # From valuation account to transfer account instead of output account
            am_vals.append(self.with_company(self.source_company_id)._prepare_account_move_vals(
                acc_valuation, transfer_account.id, journal_id, qty, description, svl_id, cost_outgoing))
                
        # For incoming move (to destination company)
        if self._is_in() and self.dest_company_id:
            # From transfer account to valuation account instead of from input account
            am_vals.append(self.with_company(self.dest_company_id)._prepare_account_move_vals(
                transfer_account.id, acc_valuation, journal_id, qty, description, svl_id, cost))
                
        return am_vals
