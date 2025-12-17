# from odoo.addons.purchase.models.purchase_order import PurchaseOrder as OriginalPurchaseOrder
from odoo.tools.misc import OrderedSet
from odoo import Command, _
from odoo.exceptions import UserError
from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_cancel(self):
        # res = super(PurchaseOrder, self).button_cancel()
        # purchase_orders_with_invoices = self.filtered(lambda po: any(i.state not in ('cancel', 'draft') for i in po.invoice_ids))
        # if purchase_orders_with_invoices:
        #     raise UserError(_("Unable to cancel purchase order(s): %s. You must first cancel their related vendor bills.", format_list(self.env, purchase_orders_with_invoices.mapped('display_name'))))
        self.write({'state': 'cancel', 'mail_reminder_confirmed': False})
        return True

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    product_price = fields.Float(string='Product Price', related='product_id.list_price', readonly=False)
    profit = fields.Float(string='Profit', help='Profit margin for this product')
    profit_rate = fields.Float(string='Profit Rate (%)', help='Profit margin as percentage')
    
    @api.onchange('profit')
    def _onchange_profit(self):
        """Update product_price and profit_rate when profit changes"""
        if self.price_unit:
            self.product_price = self.price_unit + self.profit
            # Calculate profit rate as percentage
            if self.price_unit > 0:
                self.profit_rate = (self.profit / self.price_unit) * 100
    
    @api.onchange('product_price')
    def _onchange_product_price(self):
        """Update profit and profit_rate when product_price changes"""
        # Immediate feedback and validation: if user is not in the allowed group,
        # they cannot set product_price below the product's current sale price.
        # Use _origin to get the value from DB (pre-onchange) to compare against.
        if self.price_unit:
            self.profit = self.product_price - self.price_unit
            # Calculate profit rate as percentage
            if self.price_unit > 0:
                self.profit_rate = (self.profit / self.price_unit) * 100
        if self.product_id:
            # Determine the reference sale price to compare with (pre-change)
            reference_price = self._origin.product_id.list_price if self._origin and self._origin.id else self.product_id.list_price
            if self.product_price < reference_price and not self.env.user.has_group('custom_features.group_allow_lower_product_price'):
                raise UserError(_("You are not allowed to set Product Price lower than the product's current Sale Price."))
    
    @api.onchange('profit_rate')
    def _onchange_profit_rate(self):
        """Update profit and product_price when profit_rate changes"""
        if self.price_unit and self.profit_rate is not False:
            # Calculate profit from percentage
            self.profit = (self.profit_rate / 100) * self.price_unit
            self.product_price = self.price_unit + self.profit
    
    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        """Update profit and profit_rate when price_unit changes"""
        if self.product_price:
            self.profit = self.product_price - self.price_unit
            # Calculate profit rate as percentage
            if self.price_unit > 0:
                self.profit_rate = (self.profit / self.price_unit) * 100
    
    @api.model
    def create(self, vals):
        # Enforce rule on create as well
        product_id = vals.get('product_id')
        new_price = vals.get('product_price')
        if product_id and new_price is not None and not self.env.user.has_group('custom_features.group_allow_lower_product_price'):
            # Fetch current sale price from the product
            product = self.env['product.product'].browse(product_id)
            reference_price = product.list_price
            if new_price < reference_price:
                raise UserError(_("You are not allowed to set Product Price (%.2f) lower than the product's current Sale Price (%.2f).") % (new_price, reference_price))
        return super(PurchaseOrderLine, self).create(vals)

    def write(self, vals):
        # Validate when changing product_price on existing lines
        if 'product_price' in vals and not self.env.user.has_group('custom_features.group_allow_lower_product_price'):
            new_price = vals.get('product_price')
            for line in self:
                if line.product_id and new_price is not None:
                    reference_price = line.product_id.list_price
                    if new_price < reference_price:
                        raise UserError(_("You are not allowed to set Product Price (%.2f) lower than the product's current Sale Price (%.2f).") % (new_price, reference_price))
        return super(PurchaseOrderLine, self).write(vals)