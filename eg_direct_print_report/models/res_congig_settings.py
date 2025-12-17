from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    all_print_preview = fields.Boolean(string='Direct Print', default=True)

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        icpSudo = self.env['ir.config_parameter'].sudo()  # it is given all access
        res.update(
            all_print_preview=icpSudo.get_param('eg_direct_print_report.all_print_preview'),
        )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        icpSudo = self.env['ir.config_parameter'].sudo()
        icpSudo.set_param("eg_direct_print_report.all_print_preview", self.all_print_preview)
        return res
