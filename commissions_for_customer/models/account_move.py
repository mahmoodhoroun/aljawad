from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    commission_id = fields.Many2one('sales.commission', string='Commission', readonly=True, copy=False)

    commission_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('rate', 'Rate (%)'),
        ('rate_before', 'Rate before Tax (%)')
    ], string='Commission Type', default='fixed', readonly=True)
    commission_rate = fields.Float(string='Commission Rate (%)', readonly=True)
    fixed_amount = fields.Float(string='Fixed Amount', readonly=True)
    customer_salesperson = fields.Many2one('res.partner', string='Purchasing Person', readonly=True)

    def button_draft(self):
        # Delete related commission records before setting to draft
        self._delete_related_commissions()
        return super().button_draft()

    def unlink(self):
        # Delete related commission records before deleting the invoice
        self._delete_related_commissions()
        return super().unlink()

    def _delete_related_commissions(self):
        for move in self:
            if move.move_type == 'out_invoice':
                commissions = self.env['sales.commission'].search([('invoice_id', '=', move.id)])
                if commissions:
                    _logger.info('Deleting commissions for invoice %s', move.id)
                    commissions.unlink()

    def action_post(self):
        res = super().action_post()
        self._create_invoice_commission()
        return res

    def _create_invoice_commission(self):
        auto_confirm = self.env.company.auto_confirm
        for move in self:
            if move.move_type != 'out_invoice':
                continue

            _logger.info('Checking commission for invoice %s', move.id)
            
            # Check if commission already exists for this invoice
            existing_commission = self.env['sales.commission'].search([
                ('invoice_id', '=', move.id)
            ], limit=1)
            
            if existing_commission:
                _logger.info('Commission already exists for invoice %s', move.id)
                continue
            
            # Get related sale order
            sale_order = self.env['sale.order'].search([('invoice_ids', 'in', move.ids)], limit=1)
            if not sale_order or not sale_order.customer_salesperson:
                _logger.info('No sale order found for invoice %s', move.id)
                continue

            if sale_order.fixed_amount == 0 and sale_order.commission_rate == 0:
                _logger.info('No commission found for sale order %s', sale_order.id)
                continue

            # Get salesperson
            salesperson = sale_order.user_id

            # Calculate commission amount
            commission_rate = sale_order.commission_rate
            if sale_order.commission_type == 'fixed':
                commission_amount = sale_order.fixed_amount
                vals = {
                    'customer_salesperson': sale_order.customer_salesperson.id,
                    'quotation_id': sale_order.id,
                    'invoice_id': move.id,
                    'total': move.amount_total,
                    'total_before_tax': move.amount_untaxed,
                    'paid': 0.0,  # Initially set to 0 since invoice is just posted
                    'commission_type': sale_order.commission_type,
                    'fixed_amount': sale_order.fixed_amount
                }
                commission = self.env['sales.commission'].sudo().create(vals)
                move.commission_type = sale_order.commission_type
                move.commission_rate = sale_order.commission_rate
                move.fixed_amount = sale_order.fixed_amount
                move.customer_salesperson = sale_order.customer_salesperson.id
                if auto_confirm:
                    commission.action_confirm()

            else:
                commission_amount = (move.amount_total * commission_rate) / 100
                vals = {
                    'customer_salesperson': sale_order.customer_salesperson.id,
                    'quotation_id': sale_order.id,
                    'invoice_id': move.id,
                    'total': move.amount_total,
                    'total_before_tax': move.amount_untaxed,
                    'paid': 0.0,  # Initially set to 0 since invoice is just posted
                    'commission_type': sale_order.commission_type,
                    'commission_rate': commission_rate
                }
                commission = self.env['sales.commission'].sudo().create(vals)
                if auto_confirm:
                    commission.action_confirm()
            _logger.info('Commission created for salesperson, quotation, invoice')

