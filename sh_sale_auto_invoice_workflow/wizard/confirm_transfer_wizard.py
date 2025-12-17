from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class ConfirmTransferWizard(models.TransientModel):
    _name = 'confirm.transfer.wizard'
    _description = 'Confirm Transfer Wizard'

    sale_order_id = fields.Many2one('sale.order', required=True)
    company_id = fields.Many2one('res.company', related='sale_order_id.company_id', string='Company')
    currency_id = fields.Many2one('res.currency', related='sale_order_id.currency_id', string='Currency')
    payment_journal = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ['bank', 'cash'])])
    amount = fields.Monetary(string='Amount', currency_field='currency_id', group_operator="sum")
    sale_order_amount = fields.Monetary(string='Sale Order Amount', currency_field='currency_id', related='sale_order_id.amount_total')
    # payment_ids = fields.One2many('custom.account.payment', 'wizard_id', string='Payments')
    payment_ids = fields.One2many('custom.payment.wizard.line', 'wizard_id', string='Payments')
    
    @api.onchange('payment_ids', 'payment_ids.amount')
    def _onchange_payment_lines(self):
        """Update the second line amount when the first line amount changes"""
        # if len(self.payment_ids) == 2:
            # Get the total amount from the sale order
        
        # if len(self.payment_ids) > 2 and self.payment_ids[2].amount > 0:
            # self.payment_ids[0].amount = 0.0
            # self.payment_ids[1].amount = 0.0
        amount_after3 = self.sale_order_amount - self.payment_ids[2].amount
        # else:
        total_amount = self.sale_order_amount
        
        # Get the first line amount
        first_line = self.payment_ids[0]
        first_line_amount = first_line.amount or 0.0
        
        # Ensure first line amount doesn't exceed total
        if first_line_amount > total_amount:
            first_line.amount = total_amount
            first_line_amount = total_amount
        
        # Calculate and set the second line amount
        second_line_amount = amount_after3 - first_line_amount
        second_line = self.payment_ids[1]
        second_line.amount = second_line_amount

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        sale_order_id = self.env.context.get('default_sale_order_id')
        if sale_order_id:
            sale = self.env['sale.order'].browse(sale_order_id)
            res['sale_order_id'] = sale.id
            _logger.info("payment_ids %s", sale.payment_ids)
            _logger.info("***********************************")
            res['payment_ids'] = [
                (0, 0, {
                    'payment_journal': p.payment_journal.id,
                    'amount': p.amount,
                    'currency_id': p.currency_id.id,
                }) for p in sale.payment_ids
            ]
        return res

    def action_confirm(self):
        for record in self:
            sale = record.sale_order_id

            # Validate total payments before confirming
            total_payments = sum(p.amount for p in record.payment_ids if p.amount > 0)
            if total_payments > sale.amount_total:
                raise ValidationError(_("The total amount of payments (%s) cannot be more than the order total (%s)") % (
                    format(total_payments, '.2f'), format(sale.amount_total, '.2f')))

            # Optional: remove old payments if necessary
            sale.payment_ids.unlink()

            # Copy payment records from wizard to order (only non-zero amounts)
            payment_ids = [(0, 0, {
                'amount': p.amount,
                'payment_journal': p.payment_journal.id,
                'currency_id': p.currency_id.id,
                'sale_order_id': sale.id,
                # Any other fields needed
            }) for p in record.payment_ids if p.amount > 0]

            sale.write({
                'payment_ids': payment_ids
            })

            sale.action_workflow_confirm()


class CustomPaymentWizardLine(models.TransientModel):
    _name = 'custom.payment.wizard.line'
    _description = 'Temporary payment lines in wizard'

    wizard_id = fields.Many2one('confirm.transfer.wizard', string='Wizard')
    name = fields.Char()
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                default=lambda self: self.env.company)
    payment_journal = fields.Many2one('account.journal', string='Payment Journal', domain="[('company_id', '=', company_id), ('type', 'in', ['bank', 'cash'])]", required=True)
    amount = fields.Monetary()
    currency_id = fields.Many2one(related='company_id.currency_id')
    
    @api.onchange('amount')
    def _onchange_amount(self):
        """Trigger the parent wizard's onchange method"""
        if self.wizard_id and len(self.wizard_id.payment_ids) == 2:
            # This will trigger the onchange on the wizard
            self.wizard_id._onchange_payment_lines()
