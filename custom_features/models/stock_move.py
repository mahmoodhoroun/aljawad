from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    product_category = fields.Many2one('product.category', string='Product Category', related='product_id.categ_id')
    cost_price = fields.Float(string='Cost', related='product_id.standard_price')
    product_qty_available = fields.Float(string='Quantity Available', related='product_id.qty_available')
    
