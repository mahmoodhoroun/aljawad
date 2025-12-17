from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)   

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    commission_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('rate', 'Rate (%)'),
        ('rate_before', 'Rate before Tax (%)')
    ], string='Commission Type', default='fixed', required=True, tracking=True)
    commission_rate = fields.Float(string='Commission Rate (%)', tracking=True)
    fixed_amount = fields.Float(string='Fixed Amount', tracking=True)
    customer_salesperson = fields.Many2one('res.partner', string='Purchasing Person', tracking=True)
    
    @api.constrains('fixed_amount', 'commission_rate', 'customer_salesperson')
    def _check_customer_salesperson_required(self):
        for order in self:
            if (order.fixed_amount > 0 or order.commission_rate > 0) and not order.customer_salesperson:
                raise ValidationError(_("Purchasing Person is required when Fixed Amount or Commission Rate is greater than 0."))


    def create_commission(self):
        self.ensure_one()
        commission_obj = self.env['sales.commission']
        
        vals = {
            'customer_salesperson': self.customer_salesperson.id,
            'quotation_id': self.id,
            'commission_type': self.commission_type,
            'commission_rate': self.commission_rate,
            'fixed_amount': self.fixed_amount,
            'paid': self.amount_total,
        }
        
        commission = commission_obj.create(vals)
        return {
            'name': 'Commission',
            'view_mode': 'form',
            'res_model': 'sales.commission',
            'res_id': commission.id,
            'type': 'ir.actions.act_window',
        }

    def _prepare_invoice(self):
        """Override to add commission fields to the invoice values."""
        # Call the standard method first
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        
        # Add commission fields to the invoice values
        invoice_vals.update({
            'commission_type': self.commission_type,
            'commission_rate': self.commission_rate,
            'fixed_amount': self.fixed_amount,
            'customer_salesperson': self.customer_salesperson.id if self.customer_salesperson else False,
        })
        
        _logger.info('Preparing invoice with commission values: %s', {
            'commission_type': self.commission_type,
            'commission_rate': self.commission_rate,
            'fixed_amount': self.fixed_amount,
            'customer_salesperson': self.customer_salesperson.id if self.customer_salesperson else False,
        })
        
        return invoice_vals
        
    def write(self, vals):
        # Check if any commission fields are being updated
        commission_fields = ['commission_type', 'commission_rate', 'fixed_amount', 'customer_salesperson']
        has_commission_changes = any(field in vals for field in commission_fields)
        
        # Call the original write method
        result = super(SaleOrder, self).write(vals)
        
        # If commission fields were updated, propagate changes to related invoices
        if has_commission_changes:
            for order in self:
                for invoice in order.invoice_ids:
                    _logger.info('Updating commission for invoice %s from order %s', invoice.name, order.name)
                    commission_vals = {}
                    
                    # Only update fields that were changed in the sales order
                    if 'commission_type' in vals:
                        commission_vals['commission_type'] = order.commission_type
                    if 'commission_rate' in vals:
                        commission_vals['commission_rate'] = order.commission_rate
                    if 'fixed_amount' in vals:
                        commission_vals['fixed_amount'] = order.fixed_amount
                    if 'customer_salesperson' in vals:
                        commission_vals['customer_salesperson'] = order.customer_salesperson.id if order.customer_salesperson else False
                    
                    # Update the invoice if we have values to update
                    if commission_vals:
                        invoice.write(commission_vals)
        
        return result