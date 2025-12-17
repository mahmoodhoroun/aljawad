from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lowest_selling_price = fields.Boolean(
        string='Lowest Selling Price',
        config_parameter='lowest_selling_price.lowest_selling_price'
    )
    lowest_selling_price_pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Lowest Selling Price Pricelist',
        config_parameter='lowest_selling_price.pricelist_id',
        help='Select the pricelist to be used for lowest selling price'
    )

    allow_sell_bellow_cost = fields.Boolean(
        string='Allow Sell bellow Cost',
        config_parameter='lowest_selling_price.allow_sell_bellow_cost'
    )
    
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('lowest_selling_price.lowest_selling_price', self.lowest_selling_price)
        self.env['ir.config_parameter'].sudo().set_param('lowest_selling_price.pricelist_id', self.lowest_selling_price_pricelist_id.id)
        self.env['ir.config_parameter'].sudo().set_param('lowest_selling_price.allow_sell_bellow_cost', self.allow_sell_bellow_cost)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        res.update(
            lowest_selling_price=ICPSudo.get_param('lowest_selling_price.lowest_selling_price'),
            lowest_selling_price_pricelist_id=ICPSudo.get_param('lowest_selling_price.pricelist_id'),
            allow_sell_bellow_cost=ICPSudo.get_param('lowest_selling_price.allow_sell_bellow_cost'),
        )
        return res
