from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_partner_id = fields.Many2one(
        'res.partner',
        string='Default Customer',
        config_parameter='custom_features.default_customer_id',
        # domain=[('customer_rank', '>', 0)],
        default_model='sale.order'
    )
