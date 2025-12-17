from odoo import models, fields, api


class ProductCategory(models.Model):
    _inherit = 'product.category'

    category_serial = fields.Integer(
        string='Category Serial',
        default=0,
        help='Serial number for products in this category. Auto-incremented when creating products.'
    )

    def get_next_serial(self):
        """Get the next serial number for this category and increment the counter"""
        self.ensure_one()
        current_serial = self.category_serial
        next_serial = current_serial + 1
        self.category_serial = next_serial
        return next_serial
