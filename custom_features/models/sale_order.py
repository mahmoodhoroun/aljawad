from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    purchase_order = fields.Char(string='P.O NO.')

    specialist = fields.Many2one('res.partner', string='Specialist', domain=[('is_specialist', '=', True)])
    phone_number_sale_order = fields.Char(string='Phone Number')
    
    plate_number = fields.Char(string='Plate Number')
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'partner_id' in fields_list:
            default_customer_id = self.env['ir.config_parameter'].sudo().get_param('custom_features.default_customer_id')
            if default_customer_id:
                defaults['partner_id'] = int(default_customer_id)
        return defaults

    
    def action_report_custom_invoice(self):
        """Print the custom invoice report for the first invoice related to this sale order."""
        self.ensure_one()
        # Check if the sale order is confirmed
        if self.state not in ['sale', 'done']:
            raise UserError('Cannot print invoice: Sale order is not confirmed.')

        # Get invoices related to this sale order with move_type='out_invoice'
        invoices = self.invoice_ids.filtered(lambda inv: inv.move_type == 'out_invoice')
        if not invoices:
            raise UserError('No customer invoices found for this sale order.')

        # Get the first invoice
        invoice = invoices[0]

        # Get the report and ensure the ID is included in the action
        report = self.env.ref('custom_invoice.action_report_custom_invoice')
        action = report.report_action(invoice)
        action['id'] = report.id
        return action


    def _prepare_invoice(self, ):
        """Super sale order class and update with fields"""
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'phone_number_sale_order': self.phone_number_sale_order,
            'plate_number': self.plate_number,
        })
        return invoice_vals


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.phone_number_sale_order = self.partner_id.phone
