from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    price_after_tax = fields.Float(
        string='Price After Tax',
        compute='_compute_price_after_tax',
        inverse='_inverse_price_after_tax',
        store=True,
        digits='Product Price'
    )

    @api.depends('price_unit', 'tax_ids')
    def _compute_price_after_tax(self):
        for line in self:
            if line.display_type != 'product':
                line.price_after_tax = 0.0
                continue

            taxes = line.tax_ids.compute_all(
                line.price_unit,
                line.move_id.currency_id,
                1,
                product=line.product_id,
                partner=line.move_id.partner_id
            )
            line.price_after_tax = taxes['total_included']

    def _inverse_price_after_tax(self):
        for line in self:
            if line.display_type != 'product':
                continue

            if not line.tax_ids:
                line.price_unit = line.price_after_tax
                continue

            # Calculate the price_unit that would give us this price_after_tax
            taxes = line.tax_ids
            price_unit = line.price_after_tax
            for _ in range(10):  # Iterative approximation
                taxes_computed = taxes.compute_all(
                    price_unit,
                    line.move_id.currency_id,
                    1,
                    product=line.product_id,
                    partner=line.move_id.partner_id
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