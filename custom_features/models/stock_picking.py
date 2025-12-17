from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_zero_quantities(self):
        """Set all product quantities to zero in stock picking lines with confirmation"""
        self.ensure_one()
        
        # Check if this is a draft picking
        if self.state not in ['draft', 'waiting', 'confirmed', 'assigned']:
            raise UserError("This action is only available for pickings that are not done or cancelled.")
        
        # Check if there are any move lines with products
        product_lines = self.move_ids.filtered(lambda l: l.product_id and l.product_uom_qty > 0)
        if not product_lines:
            raise UserError("No product lines with quantities found to zero.")
        
        # Return confirmation wizard
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirm Zero Quantities',
            'res_model': 'stock.picking.zero.quantities.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_line_count': len(product_lines)
            }
        }
