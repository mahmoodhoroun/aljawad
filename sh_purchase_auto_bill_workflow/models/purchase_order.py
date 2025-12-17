# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from datetime import date
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'out_receipt': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
    'in_receipt': 'supplier',
}


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _get_allowed_workflow_domain(self):
        """Get domain for workflows the current user is authorized to use"""
        return ['|', ('user_ids', '=', False), ('user_ids', 'in', self.env.user.id)]

    workflow_id = fields.Many2one(
        'sh.auto.purchase.workflow', string="Purchase Workflow",
        domain=lambda self: self._get_allowed_workflow_domain())
    allow_multiple_payment = fields.Boolean(related="workflow_id.allow_multiple_payment")
    payment_ids = fields.One2many(
        'custom.account.payment', 'purchase_order_id')
    

    @api.onchange('workflow_id')
    def _onchange_workflow_id(self):
        """Create or update payment line when workflow is selected"""
        if self.workflow_id and self.workflow_id.allow_multiple_payment:
            if not self.payment_ids:
                # Create new payment line only if none exists
                if self.workflow_id.payment_journal:
                    self.payment_ids = [(0, 0, {
                        'payment_journal': self.workflow_id.payment_journal.id,
                        'amount': self.amount_total,
                    })]
            else:
                # Update existing payment line
                self.payment_ids[0].payment_journal = self.workflow_id.payment_journal.id
                self.payment_ids[0].amount = self.amount_total


    @api.depends('order_line.price_total', 'order_line.product_qty', 'order_line.price_unit')
    def _amount_all(self):
        """Override to update payment amount when order total changes"""
        res = super(PurchaseOrder, self)._amount_all()
        for order in self:
            if order.workflow_id and order.workflow_id.allow_multiple_payment and order.payment_ids:
                order.payment_ids[0].write({'amount': order.amount_total})
        return res

    @api.onchange('order_line', 'order_line.product_qty', 'order_line.price_unit', 'order_line.taxes_id')
    def _onchange_order_lines(self):
        """Update payment amount when order lines change"""
        if self.workflow_id and self.workflow_id.allow_multiple_payment and self.payment_ids:
            self.payment_ids[0].amount = self.amount_total
    @api.onchange('partner_id')
    def get_workflow(self):
        if self.partner_id.purchase_workflow_id:
            if self.company_id.group_auto_purchase_workflow:
                self.workflow_id = self.partner_id.purchase_workflow_id
        else:
            if self.company_id.group_auto_purchase_workflow and self.company_id.purchase_workflow_id:
                self.workflow_id = self.company_id.purchase_workflow_id

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        if self.workflow_id:
            if self.workflow_id.validate_order and self.picking_ids:
                for picking in self.picking_ids:

                    picking.button_validate()


            if self.workflow_id.create_bill:
                self.action_create_invoice()

                if self.invoice_ids:

                    bill = self.invoice_ids[0]
                    if self.workflow_id.purchase_journal:
                        bill.write({
                            'journal_id': self.workflow_id.purchase_journal.id
                        })

                    if self.workflow_id.validate_bill:
                        bill.write({
                            'invoice_date': date.today()
                        })
                        bill.action_post()

                        if self.workflow_id.register_payment:
                            if not self.allow_multiple_payment:

                                payment = self.env['account.payment'].create({
                                    'currency_id': bill.currency_id.id,
                                    'amount': bill.amount_total,
                                    'payment_type': 'outbound',
                                    'partner_id': bill.commercial_partner_id.id,
                                    'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[bill.move_type],
                                    # 'ref': bill.payment_reference or bill.name,
                                    'payment_method_id': self.workflow_id.payment_method.id,
                                    'journal_id': self.workflow_id.payment_journal.id
                                })
                                payment.action_post()

                                # Get the move lines to reconcile
                                payable_lines = bill.line_ids.filtered(
                                    lambda line: line.account_id.account_type == 'liability_payable'
                                )
                                payment_lines = payment.move_id.line_ids.filtered(
                                    lambda line: line.account_id.account_type == 'liability_payable'
                                )
                                
                                # Reconcile the payment with the bill
                                (payable_lines + payment_lines).reconcile()
                            else:
                                if len(self.payment_ids) > 0:
                                    if sum(self.payment_ids.mapped('amount')) > bill.amount_total:
                                        raise UserError(_("The total amount of payments is more than the bill amount."))

                                    for payment in self.payment_ids:
                                        payment = self.env['account.payment'].create({
                                            'currency_id': bill.currency_id.id,
                                            'amount': payment.amount,
                                            'payment_type': 'outbound',
                                            'partner_id': bill.commercial_partner_id.id,
                                            'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[bill.move_type],
                                            # 'ref': bill.payment_reference or bill.name,
                                            'payment_method_id': self.workflow_id.payment_method.id,
                                            'journal_id': payment.payment_journal.id
                                        })

                                        payment.action_post()

                                        # Get the move lines to reconcile
                                        payable_lines = bill.line_ids.filtered(
                                            lambda line: line.account_id.account_type == 'liability_payable'
                                        )
                                        payment_lines = payment.move_id.line_ids.filtered(
                                            lambda line: line.account_id.account_type == 'liability_payable'
                                        )
                                        
                                        # Reconcile the payment with the bill
                                        (payable_lines + payment_lines).reconcile()
                                else:
                                    payment = self.env['account.payment'].create({
                                        'currency_id': bill.currency_id.id,
                                        'amount': bill.amount_total,
                                        'payment_type': 'outbound',
                                        'partner_id': bill.commercial_partner_id.id,
                                        'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[bill.move_type],
                                        # 'ref': bill.payment_reference or bill.name,
                                        'payment_method_id': self.workflow_id.payment_method.id,
                                        'journal_id': self.workflow_id.payment_journal.id
                                    })

                                    payment.action_post()

                                    # Get the move lines to reconcile
                                    payable_lines = bill.line_ids.filtered(
                                        lambda line: line.account_id.account_type == 'liability_payable'
                                    )
                                    payment_lines = payment.move_id.line_ids.filtered(
                                        lambda line: line.account_id.account_type == 'liability_payable'
                                    )
                                    
                                    # Reconcile the payment with the bill
                                    (payable_lines + payment_lines).reconcile()
        return False