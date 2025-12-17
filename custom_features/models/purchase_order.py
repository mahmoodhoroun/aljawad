from odoo.addons.purchase_stock.models.purchase_order import PurchaseOrder as OriginalPurchaseOrder
from odoo.tools.misc import OrderedSet
from odoo import Command, _
from odoo.exceptions import UserError

# Store the original method before monkey patching
original_button_cancel = OriginalPurchaseOrder.button_cancel

def button_cancel(self):
    """Custom implementation of button_cancel that allows cancellation of purchase orders with done receipts"""
    # Check for invoices that are not in 'cancel' or 'draft' state
    purchase_orders_with_invoices = self.filtered(lambda po: any(i.state not in ('cancel', 'draft') for i in po.invoice_ids))
    if purchase_orders_with_invoices:
        po_names = ', '.join(purchase_orders_with_invoices.mapped('display_name'))
        raise UserError(_('Unable to cancel purchase order(s): %s. You must first cancel their related vendor bills.') % po_names)
    
    # Process the cancellation of order lines and related moves
    order_lines_ids = OrderedSet()
    for order in self:
        if order.state in ('draft', 'sent', 'to approve', 'purchase'):
            order_lines_ids.update(order.order_line.ids)

    order_lines = self.env['purchase.order.line'].browse(order_lines_ids)

    moves_to_cancel_ids = OrderedSet()
    moves_to_recompute_ids = OrderedSet()
    for order_line in order_lines:
        # Only include moves that are not in 'done' state
        moves_to_cancel_ids.update(order_line.move_ids.filtered(lambda m: m.state != 'done').ids)
        
        if order_line.move_dest_ids:
            move_dest_ids = order_line.move_dest_ids.filtered(lambda move: move.state != 'done' and not move.scrapped
                                                            and move.rule_id.route_id == move.location_dest_id.warehouse_id.reception_route_id)
            moves_to_unlink = move_dest_ids.filtered(lambda m: len(m.created_purchase_line_ids.ids) > 1)
            if moves_to_unlink:
                moves_to_unlink.created_purchase_line_ids = [Command.unlink(order_line.id)]
            move_dest_ids -= moves_to_unlink
            if order_line.propagate_cancel:
                moves_to_cancel_ids.update(move_dest_ids.ids)
            else:
                moves_to_recompute_ids.update(move_dest_ids.ids)
        if order_line.group_id:
            order_line.group_id.purchase_line_ids = [Command.unlink(order_line.id)]

    # Cancel moves that are not in 'done' state
    if moves_to_cancel_ids:
        moves_to_cancel = self.env['stock.move'].browse(moves_to_cancel_ids)
        moves_to_cancel._action_cancel()

    if moves_to_recompute_ids:
        moves_to_recompute = self.env['stock.move'].browse(moves_to_recompute_ids)
        moves_to_recompute.write({'procure_method': 'make_to_stock'})
        moves_to_recompute._recompute_state()

    # Cancel pickings that are not in 'done' state
    pickings_to_cancel = self.picking_ids.filtered(lambda p: p.state != 'done' and p.state != 'cancel')
    if pickings_to_cancel:
        pickings_to_cancel.action_cancel()

    if order_lines:
        order_lines.write({'move_dest_ids': [(5, 0, 0)]})

    # Set the purchase order to canceled state
    self.write({'state': 'cancel', 'mail_reminder_confirmed': False})
    return True

# Monkey patch the button_cancel method
OriginalPurchaseOrder.button_cancel = button_cancel
