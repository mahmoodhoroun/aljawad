from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    transfer_allowed_company_ids = fields.Many2many(
        'res.company',
        'user_transfer_allowed_company_rel',
        'user_id',
        'company_id',
        string='Allowed Companies for Inventory Transfer'
    )
