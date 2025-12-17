from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    discount = fields.Float(string='Discount (%)', digits=(16, 20), default=0.0,
                            help="Discount needed.")
    total_discount = fields.Float(string="Total Discount", default=0.0,
                                  store=True, help="Total discount can be"
                                                   "specified here.")
    