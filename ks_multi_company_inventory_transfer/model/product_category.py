# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_stock_transfer_account_categ_id = fields.Many2one(
        'account.account', 'Stock Transfer Account', company_dependent=True, ondelete='restrict',
        domain="[('deprecated', '=', False)]", check_company=True,
        help="""This account will be used for internal transfers between companies.
                When doing multi-company inventory transfers, this account will be used
                as an intermediary account between the Stock Output and Stock Input accounts.""")

    @api.model
    def _get_stock_account_property_field_names(self):
        result = super(ProductCategory, self)._get_stock_account_property_field_names()
        result.append('property_stock_transfer_account_categ_id')
        return result

    @api.constrains('property_stock_transfer_account_categ_id', 'property_stock_account_input_categ_id', 
                    'property_stock_account_output_categ_id', 'property_stock_valuation_account_id')
    def _check_transfer_account(self):
        for category in self:
            if category.property_valuation == 'real_time':
                # Prevent setting the transfer account as the input, output, or valuation account
                transfer_account = category.property_stock_transfer_account_categ_id
                if transfer_account:
                    other_accounts = (category.property_stock_account_input_categ_id | 
                                     category.property_stock_account_output_categ_id | 
                                     category.property_stock_valuation_account_id)
                    if transfer_account in other_accounts:
                        raise ValidationError(_('The Stock Transfer account cannot be the same as the Stock Input, Stock Output, or Stock Valuation account.'))
