from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    cr_no = fields.Char(string='CR Number', help='Commercial Registration Number')
    is_specialist = fields.Boolean(string='Is Specialist')