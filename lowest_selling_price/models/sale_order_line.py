from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lowest_price = fields.Float(
        string='Lowest Price',
        compute='_compute_lowest_price',
        store=False,
        digits='Product Price'
    )
    lowest_selling_price = fields.Boolean(
        string='Lowest Selling Price',
        related='order_id.lowest_selling_price',
        store=False,  # No need to store since it's just for UI
        readonly=True,  # It's a related field, so it should be readonly
    )

    standard_price = fields.Float(
        string='Cost',
        related='product_id.standard_price',
        store=False,
        digits='Product Price'
    )

    @api.depends('product_id', 'product_uom')
    def _compute_lowest_price(self):
        for line in self:
            if not line.product_id:
                line.lowest_price = 0.0
                continue

            # Get the configured pricelist from settings
            lowest_price_pricelist_id = int(self.env['ir.config_parameter'].sudo().get_param('lowest_selling_price.pricelist_id', '0'))
            if not lowest_price_pricelist_id:
                line.lowest_price = 0.0
                continue

            pricelist = self.env['product.pricelist'].browse(lowest_price_pricelist_id)
            if not pricelist.exists():
                line.lowest_price = 0.0
                continue

            # Get price from the configured pricelist
            price = pricelist._get_product_price(
                line.product_id,
                line.product_uom_qty or 1.0,
                uom=line.product_uom,
                date=line.order_id.date_order
            )
            line.lowest_price = price
