from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'out_receipt': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
    'in_receipt': 'supplier',
}

class CustomAccountPayment(models.Model):
    _name = 'custom.account.payment'
    _description = 'Custom Account Payment'

    sale_order_id = fields.Many2one('sale.order', string="Sale Order", ondelete='cascade')
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", ondelete='cascade')
    payment_journal = fields.Many2one(
        'account.journal', string="Payment Journal", required=True,
        domain="[('company_id', '=', company_id), ('type', 'in', ['bank', 'cash'])]")
    amount = fields.Float(string="Amount", required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    @api.constrains('sale_order_id', 'purchase_order_id')
    def _check_order_reference(self):
        for record in self:
            if not record.sale_order_id and not record.purchase_order_id:
                raise ValidationError(_("You must specify either a Sale Order or a Purchase Order"))
            if record.sale_order_id and record.purchase_order_id:
                raise ValidationError(_("You cannot specify both Sale Order and Purchase Order"))


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_allowed_workflow_domain(self):
        """Get domain for workflows the current user is authorized to use"""
        return ['|', ('user_ids', '=', False), ('user_ids', 'in', self.env.user.sudo().id)]

    workflow_id = fields.Many2one(
        'sh.auto.sale.workflow', string="Sale Workflow",
        domain=lambda self: self._get_allowed_workflow_domain())
    allow_multiple_payment = fields.Boolean(related="workflow_id.allow_multiple_payment")
    is_boolean = fields.Boolean(related="company_id.group_auto_sale_workflow")
    payment_ids = fields.One2many(
        'custom.account.payment', 'sale_order_id')
    show_payment_section = fields.Boolean(related="workflow_id.show_payment_section")
    
    @api.onchange('workflow_id')
    def _onchange_workflow_id(self):
        """Create or update payment line when workflow is selected"""
        if self.workflow_id and self.workflow_id.allow_multiple_payment:
            if self.workflow_id.payment_journal_ids:
                for journal in self.workflow_id.payment_journal_ids:
                    self.payment_ids = [(0, 0, {
                        'payment_journal': journal.id,
                        'amount': 0,
                    })]
            else:
                if not self.payment_ids:
                    # Create new payment line only if none exists
                    if self.workflow_id.payment_journal:
                        self.payment_ids = [(0, 0, {
                            'payment_journal': self.workflow_id.payment_journal.id,
                            'amount': 0,
                        })]
                else:
                    # Update existing payment line
                    self.payment_ids[0].payment_journal = self.workflow_id.payment_journal.id
                    self.payment_ids[0].amount = 0

    @api.depends('order_line.price_total', 'order_line.product_uom_qty', 'order_line.price_unit')
    def _amount_all(self):
        """Override to update payment amount when order total changes"""
        res = super(SaleOrder, self)._amount_all()
        # Removed automatic payment amount update to allow manual control
        return res

    # @api.onchange('order_line', 'order_line.product_uom_qty', 'order_line.price_unit', 'order_line.tax_id')
    # def _onchange_order_lines(self):
    #     """Update payment amount when order lines change"""
    #     if self.workflow_id and self.workflow_id.allow_multiple_payment and self.payment_ids:
    #         self.payment_ids[0].amount = self.amount_total

    @api.onchange('partner_id')
    def get_workflow(self):
        if self.partner_id.workflow_id:
            if self.company_id.group_auto_sale_workflow:
                self.workflow_id = self.partner_id.workflow_id
        else:
            if self.company_id.group_auto_sale_workflow and self.company_id.workflow_id:
                self.workflow_id = self.company_id.workflow_id

    def action_confirm(self):        
        if self.workflow_id and self.workflow_id.allow_multiple_payment:
            # Get the view ID explicitly
            view_id = self.env.ref('sh_sale_auto_invoice_workflow.view_confirm_transfer_wizard_form').id
            
            action = {
                'name': 'Confirm Transfer Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'confirm.transfer.wizard',
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'new',
                'context': {
                    'default_sale_order_id': self.id,
                },
            }
            return action
        if self.workflow_id:
            return self.action_workflow_confirm()
        res = super(SaleOrder, self).action_confirm()
        return res
        

    def action_workflow_confirm(self):
        total_payments = 0.0

        for line in self.payment_ids:
            total_payments += line.amount
        total_payments = 0.0
        res = super(SaleOrder, self).action_confirm()
        if self.workflow_id:
            if self.workflow_id.validate_order and self.picking_ids:
                if self.workflow_id.force_transfer:
                    for picking in self.picking_ids:
                        for stock_move in picking.move_ids_without_package:
                            if stock_move.move_line_ids:
                                stock_move.move_line_ids.update({
                                    'quantity': stock_move.product_uom_qty,
                                })
                            else:
                                self.env['stock.move.line'].create({
                                    'picking_id': picking.id,
                                    'move_id': stock_move.id,
                                    'date': stock_move.date,
                                    'reference': stock_move.reference,
                                    'origin': stock_move.origin,
                                    'quantity': stock_move.product_uom_qty,
                                    'product_id': stock_move.product_id.id,
                                    'product_uom_id': stock_move.product_uom.id,
                                    'location_id': stock_move.location_id.id,
                                    'location_dest_id': stock_move.location_dest_id.id
                                })
                        picking.with_context().button_validate()
                        if picking.state != 'done':
                            sms = self.env['confirm.stock.sms'].create({
                                'pick_ids': [(4, picking.id)],
                            })
                            sms.send_sms()
                            picking.button_validate()

                else:
                    for picking in self.picking_ids:
                        picking.button_validate()
                        if picking.state != 'done':
                            sms = self.env['confirm.stock.sms'].create({
                                'pick_ids': [(4, picking.id)],
                            })
                            sms.send_sms()
                            ret = picking.button_validate()

            if self.workflow_id.create_invoice:
                for line in self.payment_ids:
                        _logger.info("in self.workflow_id.create_invoice Payment line %s: amount=%s, journal=%s", line.id, line.amount, line.payment_journal.name)
                invoice = self._create_invoices()
                if self.workflow_id.sale_journal:
                    invoice.write({
                        'journal_id': self.workflow_id.sale_journal.id,
                        'sales_workflow_id': self.workflow_id.id,
                        'type': self.workflow_id.type,
                    })

                if self.workflow_id.validate_invoice:
                    for line in self.payment_ids:
                        _logger.info("in self.workflow_id.validate_invoice Payment line %s: amount=%s, journal=%s", line.id, line.amount, line.payment_journal.name)
                    invoice.action_post()

                    if self.workflow_id.send_invoice_by_email:
                        template_id = self.env.ref(
                            'account.email_template_edi_invoice')
                        if template_id:
                            template_id.auto_delete = False
                            invoice.sudo()._generate_and_send(template_id)

                    if self.workflow_id.register_payment:
                        if not self.allow_multiple_payment:
                            # Get the receivable account for the invoice
                            receivable_account = invoice.line_ids.filtered(
                                lambda line: line.account_id.account_type == 'asset_receivable'
                            ).account_id
                            
                            if not receivable_account:
                                raise ValidationError(_('Could not find a receivable account for the invoice.'))
                            
                            payment = self.env['account.payment'].create({
                                'currency_id': invoice.currency_id.id,
                                'amount': invoice.amount_total,
                                'payment_type': 'inbound',
                                'partner_id': invoice.commercial_partner_id.id,
                                'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoice.move_type],
                                # 'ref': invoice.payment_reference or invoice.name,
                                'payment_method_id': self.workflow_id.payment_method.id,
                                'journal_id': self.workflow_id.payment_journal.id,
                                'destination_account_id': receivable_account.id,
                                'memo': invoice.name
                            })

                            payment.action_post()

                            # Create payment invoice record for auto_reconcile_payment module compatibility
                            self.env['account.payment.invoice'].create({
                                'invoice_id': invoice.id,
                                'payment_id': payment.id,
                                'reconcile_amount': invoice.amount_total
                            })

                            # Get the move lines to reconcile
                            receivable_lines = invoice.line_ids.filtered(
                                lambda line: line.account_id.account_type == 'asset_receivable'
                            )
                            payment_lines = payment.move_id.line_ids.filtered(
                                lambda line: line.account_id.account_type == 'asset_receivable'
                            )
                            
                            # Reconcile the payment with the invoice
                            (receivable_lines + payment_lines).reconcile()
                            
                            # Link payment to invoice using the proper Odoo method
                            invoice.matched_payment_ids += payment

                        else:
                            if len(self.payment_ids) > 0:
                                # total_payments = 0.0
                                # for line in self.payment_ids:
                                #     total_payments += line.amount
                                #     _logger.info("Payment line %s: amount=%s, journal=%s", line.id, line.amount, line.payment_journal.name)

                                # total_payments = 0.0
                                for line in self.payment_ids:
                                    _logger.info("Payment line %s: amount=%s, journal=%s", line.id, line.amount, line.payment_journal.name)
                                
                                if total_payments > self.amount_total:
                                    raise UserError(_("The total amount of payments (%s) cannot be more than the order total (%s)") % (
                                        format(total_payments, '.2f'), format(self.amount_total, '.2f')))

                                for payment in self.payment_ids:
                                    if payment.amount > 0:
                                        # Get the receivable account for the payment
                                        receivable_account = invoice.line_ids.filtered(
                                            lambda line: line.account_id.account_type == 'asset_receivable'
                                        ).account_id
                                        
                                        if not receivable_account:
                                            raise ValidationError(_('Could not find a receivable account for the invoice.'))
                                            
                                        payment = self.env['account.payment'].create({
                                            'currency_id': invoice.currency_id.id,
                                            'amount': payment.amount,
                                            'payment_type': 'inbound',
                                            'partner_id': invoice.commercial_partner_id.id,
                                            'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoice.move_type],
                                            # 'ref': invoice.payment_reference or invoice.name,
                                            'payment_method_id': self.workflow_id.payment_method.id,
                                            'journal_id': payment.payment_journal.id,
                                            'destination_account_id': receivable_account.id,
                                            'memo': invoice.name
                                        })

                                        payment.action_post()

                                        # Create payment invoice record for auto_reconcile_payment module compatibility
                                        self.env['account.payment.invoice'].create({
                                            'invoice_id': invoice.id,
                                            'payment_id': payment.id,
                                            'reconcile_amount': payment.amount
                                        })

                                        # Get the move lines to reconcile
                                        receivable_lines = invoice.line_ids.filtered(
                                            lambda line: line.account_id.account_type == 'asset_receivable'
                                        )
                                        payment_lines = payment.move_id.line_ids.filtered(
                                            lambda line: line.account_id.account_type == 'asset_receivable'
                                        )
                                        
                                        # Reconcile the payment with the invoice
                                        (receivable_lines + payment_lines).reconcile()
                                        
                                        # Link payment to invoice using the proper Odoo method
                                        invoice.matched_payment_ids += payment
                                        
                            # else:
                            #     payment = self.env['account.payment'].create({
                            #         'currency_id': invoice.currency_id.id,
                            #         'amount': invoice.amount_total,
                            #         'payment_type': 'inbound',
                            #         'partner_id': invoice.commercial_partner_id.id,
                            #         'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoice.move_type],
                            #         # 'ref': invoice.payment_reference or invoice.name,
                            #         'payment_method_id': self.workflow_id.payment_method.id,
                            #         'journal_id': self.workflow_id.payment_journal.id
                            #     })

                            #     payment.action_post()

                            #     # Get the move lines to reconcile
                            #     receivable_lines = invoice.line_ids.filtered(
                            #         lambda line: line.account_id.account_type == 'asset_receivable'
                            #     )
                            #     payment_lines = payment.move_id.line_ids.filtered(
                            #         lambda line: line.account_id.account_type == 'asset_receivable'
                            #     )
                                
                            #     # Reconcile the payment with the invoice
                            #     (receivable_lines + payment_lines).reconcile()

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        # Only call button_dummy if we're not in a context that should preserve payment amounts
        if not self.env.context.get('skip_payment_update'):
            self.button_dummy()
        return res