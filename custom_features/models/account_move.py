from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

import logging

class AccountMove(models.Model):
    _inherit = 'account.move'

    create_return_picking = fields.Boolean(
        string='Create Receipt Picking',
        help='If checked, system will automatically create a receipt picking when confirming the credit note',
        default=True,
        copy=False
    )
    purchase_order = fields.Char(string='P.O NO.' , compute='_compute_purchase_order', readonly=False)
    plate_number = fields.Char(string='Plate Number')
    
    def _compute_purchase_order(self):
        for order in self:
            sale_order = self.env['sale.order'].search([('invoice_ids', 'in', order.ids)], limit=1)
            if sale_order:
                order.purchase_order = sale_order.purchase_order


    def _check_credit_note_products(self):
        self.ensure_one()
        if not self.reversed_entry_id or self.move_type not in ['out_refund', 'in_refund']:
            return

        # Get all confirmed credit notes for the original invoice
        existing_credit_notes = self.env['account.move'].search([
            ('reversed_entry_id', '=', self.reversed_entry_id.id),
            ('state', '=', 'posted'),
            ('move_type', '=', self.move_type),
            ('id', '!=', self.id)
        ])

        if not existing_credit_notes:
            return

        # Create a dictionary to track returned quantities per product
        returned_quantities = {}
        for credit_note in existing_credit_notes:
            for line in credit_note.invoice_line_ids:
                if line.product_id:
                    returned_quantities[line.product_id.id] = returned_quantities.get(line.product_id.id, 0) + line.quantity

        # Check current credit note lines against previously returned quantities
        error_lines = []
        for line in self.invoice_line_ids:
            if not line.product_id:
                continue
            
            # Get the original invoice line for this product
            original_line = self.reversed_entry_id.invoice_line_ids.filtered(lambda l: l.product_id.id == line.product_id.id)
            if not original_line:
                continue

            previously_returned = returned_quantities.get(line.product_id.id, 0)
            total_return_quantity = previously_returned + line.quantity

            if total_return_quantity > original_line.quantity:
                error_lines.append({
                    'product': line.product_id.name,
                    'available': original_line.quantity - previously_returned,
                    'attempted': line.quantity
                })

        if error_lines:
            error_message = "Cannot confirm credit note due to quantity limitations:\n"
            for error in error_lines:
                error_message += f"- {error['product']}: Attempting to return {error['attempted']} units but only {error['available']} available to return\n"
            raise ValidationError(error_message)

    def action_post(self):
        for move in self:
            if move.move_type in ['out_refund', 'in_refund']:
                move._check_credit_note_products()

        res = super(AccountMove, self).action_post()
        
        for move in self:
            logging.error("**************** move")
            logging.error(move)
            if move.create_return_picking and move.reversed_entry_id:
                # Get the original invoice/bill
                original_document = move.reversed_entry_id
                logging.error("**************** original_document")
                logging.error(original_document)

                if move.move_type == 'out_refund':
                    # Customer Credit Note
                    # Find related sale order
                    sale_order = self.env['sale.order'].search([
                        ('invoice_ids', 'in', [original_document.id])
                    ], limit=1)

                    logging.error("**************** sale_order")
                    logging.error(sale_order)
                    
                    if sale_order and sale_order.picking_ids:
                        # Filter for completed delivery pickings
                        delivery_picking = sale_order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state == 'done')
                        if delivery_picking:
                            picking = delivery_picking.sorted(lambda p: p.date, reverse=True)[0]
                            return self._create_return_picking(move, picking)

                elif move.move_type == 'in_refund':
                    # Vendor Credit Note
                    # Find related purchase order
                    purchase_order = self.env['purchase.order'].search([
                        ('invoice_ids', 'in', [original_document.id])
                    ], limit=1)

                    logging.error("**************** purchase_order")
                    logging.error(purchase_order)

                    if purchase_order and purchase_order.picking_ids:
                        # Filter for completed receipt pickings
                        receipt_picking = purchase_order.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming' and p.state == 'done')
                        if receipt_picking:
                            picking = receipt_picking.sorted(lambda p: p.date, reverse=True)[0]
                            return self._create_return_picking(move, picking)
        return res

    def _create_return_picking(self, move, picking):
        # Create return wizard
        wizard = self.env['stock.return.picking'].with_context(
            active_id=picking.id,
            active_model='stock.picking'
        ).create({
            'picking_id': picking.id,
        })
        
        # Delete existing return lines
        wizard.product_return_moves.unlink()
        
        # Add return lines based on credit note lines
        for line in move.invoice_line_ids:
            if line.product_id.type in ['product', 'consu']:
                logging.error("**************** Processing product: %s", line.product_id.name)
                
                # Try to find matching move line
                move_line = picking.move_ids.filtered(lambda m: m.product_id == line.product_id)
                # Handle case where multiple move lines exist for the same product
                move_line_id = move_line[0].id if move_line else False
                
                # Create return line regardless of move_line existence
                return_line = self.env['stock.return.picking.line'].create({
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'wizard_id': wizard.id,
                    'move_id': move_line_id,
                })
                logging.error("**************** Created return line for: %s", line.product_id.name)
        
        # Return the wizard view
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.return.picking',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
            'context': {'active_id': picking.id}
        }
    
    def unlink(self):
        for move in self:
            if move.move_type in ['out_refund', 'in_refund']:
                raise UserError("You cannot delete a confirmed Invoice/Credit Note")
        return super(AccountMove, self).unlink()
    

    def button_rest_draft(self):
        for move in self:
            move.button_draft()

    def action_zero_quantities(self):
        """Set all product quantities to zero in credit note lines with confirmation"""
        self.ensure_one()
        
        # Check if this is a credit note
        if self.move_type not in ['out_refund', 'in_refund']:
            raise UserError("This action is only available for credit notes.")
        
        # Check if there are any invoice lines with products
        product_lines = self.invoice_line_ids.filtered(lambda l: l.product_id and l.quantity > 0)
        if not product_lines:
            raise UserError("No product lines with quantities found to zero.")
        
        # Return confirmation wizard
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirm Zero Quantities',
            'res_model': 'account.move.zero.quantities.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
                'default_line_count': len(product_lines)
            }
        }