# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import fields, models


class ImportOperation(models.TransientModel):
    _inherit = 'import.operation'

    salla_filter_type = fields.Selection(
        string='Filter Type',
        selection=[
            ('all', 'All'),
            ('id', 'By ID'),
            ('date', 'By Date')
        ],
        default='all',
        required=True,
    )
    salla_object_id = fields.Char('Object ID')
    salla_from_date = fields.Datetime()
    salla_to_date = fields.Datetime()
    salla_enable_keyword = fields.Boolean() 
    salla_product_keyword = fields.Char() # product name(full name or a part) or sku
    salla_order_status = fields.Selection([
        ('566146469','Under Review'),
        ('1473353380','Pending Payment'),
        ('814202285','Shipped'),
        ('349994915','Delivery in Progress'),
        ('1723506348','Delivered'),
        ('1298199463','Completed'),
        ('525144736','Canceled'),
    ])
    salla_import_variants_as_products = fields.Boolean(
        string='Import Variants as Separate Products',
        default=False,
        help='If enabled, each variant will be imported as a separate product instead of as product variants'
    )

    def salla_get_filter(self):
        kw = {
                'filter_type': self.salla_filter_type,
                'salla_product_keyword':self.salla_product_keyword,
                'salla_enable_keyword':self.salla_enable_keyword,
                'salla_order_status': self.salla_order_status,
                'salla_import_variants_as_products': self.salla_import_variants_as_products,
              }
        if self.salla_filter_type == 'id':
            kw['object_id'] = self.salla_object_id
        if self.salla_filter_type == "date":
            kw.update({
                'salla_from_date': self.salla_from_date,
                'salla_to_date': self.salla_to_date,
            })
        return kw
