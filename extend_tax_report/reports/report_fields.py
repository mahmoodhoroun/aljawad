from odoo import api, models, _


class Reportfields(models.AbstractModel):
    _inherit = 'account.common.report'
    
    tax = fields.Selection([
        ('15', '15%'),
        ('5', '5%'),
    ], required=True, string='Tax Amount')
  