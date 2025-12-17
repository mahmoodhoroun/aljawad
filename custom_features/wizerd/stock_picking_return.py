from odoo import _, api, fields, models
from odoo.tools.float_utils import float_is_zero


class StockReturnPickingExchangeLine(models.TransientModel):
    _name = "stock.return.picking.exchange.line"
    _description = "Return Picking Exchange Line"
    
    product_id = fields.Many2one('product.product', string="Exchange Product", required=True)
    quantity = fields.Float("Quantity", digits='Product Unit of Measure', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id')
    wizard_id = fields.Many2one('stock.return.picking', string="Wizard")
    

class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'
    
    exchange_product_lines = fields.One2many(
        'stock.return.picking.exchange.line',
        'wizard_id',
        string="Exchange Products"
    )
    
    def action_create_returns(self):
        self.ensure_one()
        new_picking = self._create_return()
        new_picking.button_validate()
        return {
            'name': _('Returned Picking'),
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': new_picking.id,
            'type': 'ir.actions.act_window',
            'context': self.env.context,
        }

    def action_create_exchanges(self):
        """ Override to create a return picking and a separate exchange picking """
        # Create the return picking first (for the returned products)
        new_picking = self._create_return()
        new_picking.button_validate()
        # Only create exchange picking if we have exchange products
        if not self.exchange_product_lines:
            return {
                'name': _('Returned Picking'),
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'res_id': new_picking.id,
                'type': 'ir.actions.act_window',
                'context': self.env.context,
            }
        
        # Create a list of procurements only for the exchange products
        proc_list = []
        
        # Add the exchange products to the procurement list
        for line in self.exchange_product_lines:
            if float_is_zero(line.quantity, precision_rounding=line.uom_id.rounding):
                continue
                
            # Use the same procurement values as the original method
            proc_values = {
                'group_id': self.picking_id.group_id,
                'date_planned': fields.Datetime.now(),
                'warehouse_id': self.picking_id.picking_type_id.warehouse_id,
                'partner_id': self.picking_id.partner_id.id,
                'company_id': self.picking_id.company_id,
            }
            
            # Create a procurement for each exchange product
            proc_list.append(self.env["procurement.group"].Procurement(
                line.product_id, 
                line.quantity, 
                line.uom_id,
                self.picking_id.location_dest_id,  # Destination location
                f"{line.product_id.display_name} (Exchange)",  # Name
                self.picking_id.origin,  # Origin
                self.picking_id.company_id,  # Company
                proc_values,  # Values
            ))
        
        # Run the procurements to create the exchange picking
        if proc_list:
            self.env['procurement.group'].run(proc_list)
        
        # Return the action to view the return picking
        return {
            'name': _('Returned Picking'),
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': new_picking.id,
            'type': 'ir.actions.act_window',
            'context': self.env.context,
        }
