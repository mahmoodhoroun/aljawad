from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    po_order_discount = fields.Boolean(
        string="Purchase Order Discount"
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super(PurchaseOrder, self).default_get(fields_list)
        _logger.info("defaults: %s", defaults)    
        _logger.info("/***********************************************")    
        if 'po_order_discount' in fields_list:
            param_value = self.env['ir.config_parameter'].sudo().get_param('purchase_discount_total.po_order_discount') == 'True'
            defaults['po_order_discount'] = param_value
        return defaults


    @api.depends('company_id')
    def _compute_po_order_discount(self):
        for order in self:
            order.po_order_discount = self.env['ir.config_parameter'].sudo().get_param('purchase_discount_total.po_order_discount') == 'True'
    
    discount_type = fields.Selection(
        [('percent', 'Percentage'), ('amount', 'Amount')],
        string='Discount type',
        default='percent', help="Type of discount.")
    discount_rate = fields.Float('Discount Rate', digits=(16, 2),
                                 help="Give the discount rate.")
    
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True,
                                     readonly=True, compute='_amount_all',
                                     help="Untaxed amount before applying discount")
    amount_tax = fields.Monetary(string='Taxes', store=True,
                                 readonly=True, compute='_amount_all',
                                 help="Tax amount")
    amount_total = fields.Monetary(string='Total', store=True,
                                   readonly=True, compute='_amount_all',
                                   help="Total amount after applying discount")
    amount_discount = fields.Monetary(string='Discount', store=True,
                                      compute='_amount_all', readonly=True,
                                      help="Discount amount")

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """Compute the total amounts of the PO."""
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amount_discount += (
                    line.product_qty * line.price_unit * line.discount) / 100
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_discount': amount_discount,
                'amount_total': amount_untaxed + amount_tax,
            })


    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def supply_rate(self):
        """This function calculates supply rates based on change of
        discount_type, discount_rate and invoice_line_ids"""
        for order in self:
            if order.discount_type == 'percent':
                for line in order.order_line:
                    line.discount = order.discount_rate
            else:
                total = 0.0
                for line in order.order_line:
                    total += round((line.product_qty * line.price_unit))
                if total > 0 and order.discount_rate != 0:
                    for line in order.order_line:
                        # Calculate line total
                        line_total = line.product_qty * line.price_unit
                        # Calculate proportional discount for this line
                        line_discount_amount = (line_total / total) * order.discount_rate
                        # Convert amount to percentage for this specific line
                        line.discount = (line_discount_amount / line_total) * 100 if line_total else 0.0
                else:
                    for line in order.order_line:
                        line.discount = 0.0
