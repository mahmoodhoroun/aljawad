from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    po_order_discount = fields.Boolean(string="Purchase Discount Approval", config_parameter='purchase_discount_total.po_order_discount')
    
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('purchase_discount_total.po_order_discount', self.po_order_discount)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        res.update(
            po_order_discount=ICPSudo.get_param('purchase_discount_total.po_order_discount') == 'True',
        )
        return res