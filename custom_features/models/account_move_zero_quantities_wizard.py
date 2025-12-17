from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountMoveZeroQuantitiesWizard(models.TransientModel):
    _name = 'account.move.zero.quantities.wizard'
    _description = 'Zero Quantities Confirmation Wizard'

    move_id = fields.Many2one('account.move', string='Credit Note', required=True)
    line_count = fields.Integer(string='Number of Lines', readonly=True)
    
    def action_confirm_zero_quantities(self):
        """Confirm and execute zeroing quantities"""
        self.ensure_one()
        
        if not self.move_id:
            raise UserError("No credit note selected.")
        
        # Check if the move is in draft state
        if self.move_id.state != 'draft':
            raise UserError("Can only modify quantities in draft credit notes.")
        
        # Set quantities to zero for all product lines
        product_lines = self.move_id.invoice_line_ids.filtered(lambda l: l.product_id)
        for line in product_lines:
            line.quantity = 0.0
        
        # Recompute the invoice totals
        # self.move_id._compute_amount()
        
        return {'type': 'ir.actions.act_window_close'}
    
    def action_cancel(self):
        """Cancel the operation"""
        return {'type': 'ir.actions.act_window_close'}
