from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_after_tax = fields.Float(
        string='Price After Tax',
        compute='_compute_price_after_tax',
        inverse='_inverse_price_after_tax',
        store=True,
        digits='Product Price'
    )
    categ_id = fields.Many2one(related='product_id.categ_id', string='Category', readonly=True)
                    
    @api.depends('price_unit', 'tax_id')
    def _compute_price_after_tax(self):
        for line in self:
            taxes = line.tax_id.compute_all(
                line.price_unit,
                line.order_id.currency_id,
                1,
                product=line.product_id,
                partner=line.order_id.partner_id
            )
            line.price_after_tax = taxes['total_included']

    def _inverse_price_after_tax(self):
        for line in self:
            if not line.tax_id:
                line.price_unit = line.price_after_tax
                continue

            # Calculate the price_unit that would give us this price_after_tax
            taxes = line.tax_id
            price_unit = line.price_after_tax
            for _ in range(10):  # Iterative approximation
                taxes_computed = taxes.compute_all(
                    price_unit,
                    line.order_id.currency_id,
                    1,
                    product=line.product_id,
                    partner=line.order_id.partner_id
                )
                if abs(taxes_computed['total_included'] - line.price_after_tax) < 0.01:
                    break
                # Adjust price_unit based on the difference
                price_unit = price_unit * (line.price_after_tax / taxes_computed['total_included'])
            
            line.price_unit = price_unit

    @api.onchange('price_after_tax')
    def _onchange_price_after_tax(self):
        if self.price_after_tax:
            self._inverse_price_after_tax()

    def action_view_stock_details(self):
        self.ensure_one()
        if not self.product_id:
            raise UserError('Please select a product first')

        # Create wizard
        wizard = self.env['stock.details.wizard'].create({
            'product_id': self.product_id.id,
        })

        return {
            'name': 'Stock Details',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.details.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }

    stock_display = fields.Char(string="Stock Available", compute="_compute_stock_display")

    @api.depends('product_id.qty_available', 'product_id.stock_quant_ids')
    def _compute_stock_display(self):
        """ Compute stock display format: main_warehouse_qty(total_warehouses_qty)
            main_warehouse_qty: sum of quantities in all internal locations under main warehouse
            total_warehouses_qty: sum of quantities in all internal locations under all allowed warehouses
        """
        user = self.env.user
        allowed_warehouses = user.allowed_warehouse_ids or self.env['stock.warehouse'].sudo().search([])
        
        # Get main warehouse (first from allowed warehouses or first overall if none allowed)
        main_warehouse = allowed_warehouses[0] if allowed_warehouses else self.env['stock.warehouse'].sudo().search([], limit=1)

        # Get all internal locations under main warehouse
        main_warehouse_locations = self.env['stock.location'].sudo().search([
            ('id', 'child_of', main_warehouse.view_location_id.id),
            ('usage', '=', 'internal')
        ])

        # Get all internal locations under all allowed warehouses
        all_warehouse_locations = self.env['stock.location'].sudo().search([
            ('id', 'child_of', allowed_warehouses.mapped('view_location_id').ids),
            ('usage', '=', 'internal')
        ])

        for line in self:
            product = line.product_id
            if product:
                # Get quantity in all internal locations under main warehouse
                main_warehouse_qty = sum(product.sudo().stock_quant_ids.filtered(
                    lambda q: q.location_id.id in main_warehouse_locations.ids
                ).mapped('quantity'))

                # Get total quantity across all internal locations in all warehouses
                total_warehouses_qty = sum(product.sudo().stock_quant_ids.filtered(
                    lambda q: q.location_id.id in all_warehouse_locations.ids
                ).mapped('quantity'))

                # Format the result: main_warehouse_qty(total_warehouses_qty)
                line.stock_display = f"{int(main_warehouse_qty)}({int(total_warehouses_qty)})"
            else:
                line.stock_display = "0(0)"