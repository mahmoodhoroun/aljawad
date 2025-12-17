from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPickingZeroQuantitiesWizard(models.TransientModel):
    _name = 'stock.picking.zero.quantities.wizard'
    _description = 'Stock Picking Zero Quantities Confirmation Wizard'

    picking_id = fields.Many2one('stock.picking', string='Stock Picking', required=True)
    line_count = fields.Integer(string='Number of Lines', readonly=True)
    
    def action_confirm_zero_quantities(self):
        """Confirm and execute zeroing quantities"""
        self.ensure_one()
        
        if not self.picking_id:
            raise UserError("No stock picking selected.")
        
        # Check if the picking is in a valid state
        if self.picking_id.state not in ['draft', 'waiting', 'confirmed', 'assigned']:
            raise UserError("Can only modify quantities in draft or confirmed pickings.")
        
        # Set quantities to zero for all product lines
        product_lines = self.picking_id.move_ids.filtered(lambda l: l.product_id)
        for line in product_lines:
            line.product_uom_qty = 0.0
            # Also set demand quantity to zero if it exists
            if hasattr(line, 'quantity_done'):
                line.quantity_done = 0.0
        
        return {'type': 'ir.actions.act_window_close'}
    
    def action_cancel(self):
        """Cancel the operation"""
        return {'type': 'ir.actions.act_window_close'}
