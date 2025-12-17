from odoo import models, fields, api

class StockDetailsWizard(models.TransientModel):
    _name = 'stock.details.wizard'
    _description = 'Stock Details per Location'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    warehouse_stock_ids = fields.One2many('warehouse.stock.line', 'wizard_id', string='Location Stock')
    product_cost = fields.Float(string='Product Cost', readonly=True, related='product_id.standard_price')
    
    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.product_id:
            # Get user's allowed warehouses
            user = self.env.user
            warehouses = user.allowed_warehouse_ids or self.env['stock.warehouse'].sudo().search([])
            
            for warehouse in warehouses:
                # Get all internal locations under this warehouse
                locations = self.env['stock.location'].sudo().search([
                    ('id', 'child_of', warehouse.view_location_id.id),
                    ('usage', '=', 'internal')
                ])
                
                # Create a line for each location with stock
                for location in locations:
                    quantity = sum(res.product_id.sudo().stock_quant_ids.filtered(
                        lambda q: q.location_id.id == location.id
                    ).mapped('quantity'))
                    
                    if quantity > 0 or quantity < 0:  # Only show locations with stock
                        self.env['warehouse.stock.line'].create({
                            'wizard_id': res.id,
                            'warehouse_name': warehouse.name,
                            'location_name': location.complete_name,
                            'quantity': int(quantity)
                        })
        return res

class WarehouseStockLine(models.TransientModel):
    _name = 'warehouse.stock.line'
    _description = 'Location Stock Line'
    _order = 'warehouse_name, location_name'

    wizard_id = fields.Many2one('stock.details.wizard', string='Wizard')
    warehouse_name = fields.Char(string='Warehouse', readonly=True)
    location_name = fields.Char(string='Location', readonly=True)
    quantity = fields.Integer(string='Quantity', readonly=True)
