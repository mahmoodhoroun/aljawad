from odoo import fields, models, api


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    is_print_preview = fields.Boolean(string='Direct Print')

    @api.model
    def get_report_print_preview(self, xml_id):
        all_print_preview = self.env['ir.config_parameter'].sudo().get_param('eg_direct_print_report.all_print_preview')
        report_id = self.search([('id', '=', xml_id)])
        return True if all_print_preview == 'True' or report_id.is_print_preview else False

    def _get_readable_fields(self):
        data = super()._get_readable_fields()
        data.add('is_print_preview')
        return data
