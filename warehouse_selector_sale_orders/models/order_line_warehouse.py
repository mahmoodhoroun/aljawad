from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class OrderLineWarehouse(models.Model):
    _name = 'order.line.warehouse'
    _description = 'Order Line Warehouse Configuration'

    so_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    product_id = fields.Many2one(related='so_line_id.product_id', string='Product', store=True)
    qty = fields.Float(string='Quantity')
    warehouse_id = fields.Many2one('stock.warehouse')
    uom_id = fields.Many2one(related='so_line_id.product_uom', string='Unit of Measure')
    available_qty_product = fields.Float(string='Current Available Qty', compute='_compute_available_qty_product', store=True)

    @api.depends('warehouse_id')
    def _compute_available_qty_product(self):
        for record in self:
            if record.so_line_id and record.warehouse_id:
                # warehouse_id = record.warehouse_id
                available = record.so_line_id.product_id.with_context(warehouse=record.warehouse_id.sudo().id).qty_available
                record.available_qty_product = available

    @api.constrains('qty')
    def _check_qty(self):
        order_line_warehouses = self.env['order.line.warehouse'].search([('so_line_id', '=', self.so_line_id.id)])
        for record in self:
            qty = sum(order_line_warehouses.mapped('qty'))
            if qty > record.so_line_id.product_uom_qty:
                raise ValidationError('The total quantity cannot be more than the order line quantity.')

    @api.constrains('warehouse_id')
    def _chek_duplicate_warehouse(self):
        for rec in self:
            record = self.search([('warehouse_id', '=', rec.warehouse_id.id), ('so_line_id', '=', rec.so_line_id.id)])
            if record and len(record) > 1:
                raise ValidationError(_("%s You've already picked a warehouse.") % rec.warehouse_id.name)
