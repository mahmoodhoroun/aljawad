from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_select_warehouse_qty = fields.Boolean(string='Auto Select Warehouse Quantity', config_parameter='sale.auto_select_warehouse_qty',
                                               help='Auto select warehouse quantity from different warehouse if main warehouse quantity is not fulfilled.')
