from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_id = fields.Many2one('sale.order', string='Sale Order', compute='_compute_sale_id')

    def _compute_sale_id(self):
        for move in self:
            move.sale_id = self.env['sale.order'].search([('invoice_ids', 'in', move.ids)], limit=1)

    def action_print_custom_invoice(self):
        """Print the custom invoice report with direct print support."""
        self.ensure_one()
        # Get the report and ensure the ID is included in the action
        report = self.env.ref('custom_invoice.action_report_custom_invoice')
        action = report.report_action(self)
        action['id'] = report.id
        return action

