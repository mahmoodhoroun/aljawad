from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    branch_code = fields.Char(string='Branch Code')
    english_company_name = fields.Char(string='English Company Name')
    english_city_name = fields.Char(string='English City Name')