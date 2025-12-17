# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_is_zero

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class KsStockTransferMultiCompany(models.Model):
    _name = 'multicompany.transfer.stock'
    _description = "Multi Company Inventory Transfer"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(readonly=True, copy=False)
    ks_transfer_to = fields.Many2one('res.company', string='Company To', required=True, tracking=True)
    ks_transfer_to_location = fields.Many2one('stock.location', string='Destination Location', required=True)
    ks_transfer_from = fields.Many2one('res.company', string='Company From',
                                       default=lambda self: self.env.user.company_id, required=True,
                                       tracking=True)
    ks_transfer_from_location = fields.Many2one('stock.location', string='Source Location', required=True)
    ks_memo_for_transfer = fields.Char('Internal Notes')
    ks_schedule_date = fields.Date('Schedule Date', default=lambda *a: fields.Datetime.now(), required=True,
                                   tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('in_progress', 'In Progress'), ('posted', 'Posted')],
                             default='draft', tracking=True, copy=False)
    ks_multicompany_transfer_stock_ids = fields.One2many('multicompany.transfer.stock.line',
                                                         'ks_multicompany_transfer_id')
    ks_stock_picking_ids = fields.Many2many('stock.picking', copy=False)
    ks_movement_completed = fields.Boolean(string='Movement Completed', compute='compute_ks_movement_completed',
                                           default=True)

    # @api.model
    # def _get_allowed_companies_domain(self):
    #     """Get domain for companies based on user's transfer_allowed_company_ids"""
    #     user = self.env.user
    #     _logger.info(f"User: {user.name}, Transfer allowed companies: {user.transfer_allowed_company_ids.mapped('name')}")
    #     if user.transfer_allowed_company_ids:
    #         # If user has specific companies allowed for transfer, use those
    #         domain = [('id', 'in', user.transfer_allowed_company_ids.ids)]
    #         _logger.info(f"Using transfer_allowed_company_ids domain: {domain}")
    #         return domain
    #     else:
    #         # If no specific companies are set, allow all companies user has access to
    #         domain = [('id', 'in', user.sudo().company_ids.ids)]
    #         _logger.info(f"Using company_ids domain: {domain}")
    #         return domain



    @api.depends('ks_movement_completed')
    def compute_ks_movement_completed(self):
        for rec in self:
            if rec.ks_stock_picking_ids.filtered(lambda x: x.state != 'done'):
                rec.ks_movement_completed = False
            else:
                rec.ks_movement_completed = True

    # @api.onchange('ks_transfer_to', 'ks_transfer_from')
    # def ks_company_onchange(self):
    #     if self.ks_transfer_to_location.company_id.id != self.ks_transfer_to.id:
    #         self.ks_transfer_to_location = False
    #     if self.ks_transfer_from_location.company_id.id != self.ks_transfer_from.id:
    #         self.ks_transfer_from_location = False
    #     self.ks_transfer_to_location = self.env['stock.location'].sudo().search([('usage', '=', 'internal'), ('company_id', '=', self.ks_transfer_to.id)], limit=1)
    #     self.ks_transfer_from_location = self.env['stock.location'].sudo().search([('usage', '=', 'internal'), ('company_id', '=', self.ks_transfer_from.id)], limit=1)

    def unlink(self):
        if sum(self.ks_multicompany_transfer_stock_ids.mapped('ks_reserved_availability')) > 0:
            raise ValidationError("This Record can't be deleted as the quantities are also reserved. ")
        return super(KsStockTransferMultiCompany, self).unlink()

    def ks_update_product_costs_in_destination_company(self):
        """
        Update product costs in the destination company to match costs from the source company
        before processing transfer lines.
        """
        if self.ks_transfer_to.id != self.ks_transfer_from.id:
            _logger.info("Updating product costs in destination company %s from source company %s", 
                        self.ks_transfer_to.name, self.ks_transfer_from.name)
            
            for stock_line in self.ks_multicompany_transfer_stock_ids:
                product_id = stock_line.ks_product_id
                
                # Get the product cost from the source company
                source_product = self.env['product.product'].sudo().with_company(self.ks_transfer_from).browse(product_id.id)
                source_cost = source_product.standard_price
                
                # Update the product cost in the destination company
                dest_product = self.env['product.product'].sudo().with_company(self.ks_transfer_to).browse(product_id.id)
                if dest_product.exists():
                    dest_product.write({'standard_price': source_cost})
                    _logger.info("Updated cost for product %s in company %s: %s -> %s", 
                                product_id.name, self.ks_transfer_to.name, dest_product.standard_price, source_cost)
                else:
                    _logger.warning("Product %s not found in destination company %s", 
                                   product_id.name, self.ks_transfer_to.name)

    def ks_confirm_inventory_transfer(self):
        # Update product costs in destination company before processing transfer lines
        self.ks_update_product_costs_in_destination_company()
        
        for stock_line in self.ks_multicompany_transfer_stock_ids:
            ks_lot_serial = stock_line.ks_move_line_ids.filtered(
                lambda move: move.ks_lot_id.id == False and move.ks_product_id.tracking != 'none')
            if ks_lot_serial:
                for move_line in stock_line.ks_move_line_ids:
                    if not move_line.ks_lot_id:
                        raise UserError(_('No Lot/Serial Number found for %s.' % move_line.ks_product_id.name))
                    if not move_line.ks_receiver_lot_id:
                        raise UserError(
                            _('No Receivers Lot/Serial Number found for %s.' % move_line.ks_product_id.name))
        move_lines = self.ks_prepare_move_lines(self.ks_multicompany_transfer_stock_ids)
        self.name = self.env['ir.sequence'].with_context(ir_sequence_date=self.ks_schedule_date). \
            next_by_code("multicompany.transfer.inventory")

        #  For Internal picking
        if self.ks_transfer_to.id == self.ks_transfer_from.id:
            ks_internal_picking_type = self.env['stock.picking.type'].sudo().with_company(self.ks_transfer_from).with_context(active_test=False).search([
                ('code', '=', 'internal'),
                ('warehouse_id.company_id', '=', self.ks_transfer_from.id),
            ], limit=1)

            if not ks_internal_picking_type:
                raise ValidationError("Internal Picking is not defined for %s" % (self.ks_transfer_to.name))
            ks_internal_picking_id = self.env['stock.picking'].sudo().with_company(self.ks_transfer_from).create({
                'picking_type_id': ks_internal_picking_type.id,
                'location_id': self.ks_transfer_from_location.id,
                'partner_id': self.ks_transfer_from.partner_id.id,
                'scheduled_date': self.ks_schedule_date,
                'move_ids': move_lines,
                'origin': self.name,
                'location_dest_id': self.ks_transfer_to_location.id,
            })
            self.ks_unreserve_before_validate()
            ks_internal_picking_id.action_assign()
            self.ks_update_lot_serial(ks_internal_picking_id, self.ks_multicompany_transfer_stock_ids)
            ks_internal_picking_id.button_validate()
            self.state = 'posted'
            self.ks_stock_picking_ids = [(6, 0, [ks_internal_picking_id.id])]
        else:
            # for another company picking
            picking_type = self.env['stock.picking.type'].sudo().with_company(self.ks_transfer_from).search([
                ('code', '=', 'outgoing'),
                ('warehouse_id.company_id', '=', self.ks_transfer_from.id),
            ], limit=1)
            if not picking_type:
                raise ValidationError("Outgoing Picking is not defined for %s" % (self.ks_transfer_from.name))

            ks_location = self.env['stock.location'].sudo().search([('usage', '=', 'transit')], order='company_id desc',
                                                            limit=1)
            if not ks_location:
                self.env['stock.location'].sudo().with_company(self.ks_transfer_from).create({'name': _('Inter-warehouse transit'),
                                                   'usage': 'transit',
                                                   'company_id': False,
                                                   'location_id': False})
            outgoing_move_lines = self.ks_outgoing_move_line(self.ks_multicompany_transfer_stock_ids)
            outgoing_move_line_ids = self.ks_outgoing_move_line_ids(self.ks_multicompany_transfer_stock_ids)
            ks_picking_from_id = self.env['stock.picking'].sudo().with_company(self.ks_transfer_to).create({
                'picking_type_id': picking_type.id,
                'location_id': self.ks_transfer_from_location.id,
                'partner_id': self.ks_transfer_to.partner_id.id,
                'scheduled_date': self.ks_schedule_date,
                'move_ids': outgoing_move_lines,
                'move_line_ids': outgoing_move_line_ids,
                'origin': self.name,
                'location_dest_id': self.env['stock.location'].sudo().with_company(self.ks_transfer_from).search([('usage', '=', 'transit'), '|',
                                                                       (
                                                                           'company_id', '=',
                                                                           self.ks_transfer_from.id),
                                                                       ('company_id', '=', False),

                                                                       ], limit=1, order='company_id desc').id,
            })
            ext_move = self.env['stock.move.line'].search(
                [('picking_id', '=', ks_picking_from_id.id), ('ks_custom_line', '=', False)])
            ext_move.unlink()
            self.ks_unreserve_before_validate()
            ks_picking_from_id.action_assign()
            self.ks_update_lot_serial(ks_picking_from_id, self.ks_multicompany_transfer_stock_ids)
            sms_data = ks_picking_from_id.button_validate()
            if type(sms_data) != bool:
                if sms_data and sms_data.get('res_model', False) and sms_data.get(
                        'res_model') == 'confirm.stock.sms':
                    wizard = self.env[(sms_data.get('res_model'))].browse(sms_data.get('res_id'))
                    if wizard.dont_send_sms():
                        ks_picking_from_id.button_validate()
            picking_incoming_id = self.env['stock.picking.type'].sudo().with_company(self.ks_transfer_to).search([
                ('code', '=', 'incoming'),
                ('warehouse_id.company_id', '=', self.ks_transfer_to.id),
            ], limit=1)
            if not picking_incoming_id:
                raise ValidationError("Incoming Picking is not defined for %s" % (self.ks_transfer_to.name))
            incoming_move_lines = self.ks_incoming_move_line(self.ks_multicompany_transfer_stock_ids)
            incoming_move_line_ids = self.ks_incoming_move_line_ids(self.ks_multicompany_transfer_stock_ids)
            _logger.info("picking_incoming_id %s,  %s", picking_incoming_id.name, picking_incoming_id.id)
            ks_picking_to_id = self.env['stock.picking'].sudo().with_company(self.ks_transfer_to).create({
                'picking_type_id': picking_incoming_id.id,
                'location_id': self.env['stock.location'].sudo().with_company(self.ks_transfer_to).search([('usage', '=', 'transit'), '|',
                                                                  ('company_id', '=', self.ks_transfer_to.id),
                                                                  ('company_id', '=', False),

                                                                  ], limit=1, order='company_id desc').id,
                'partner_id': self.ks_transfer_from.partner_id.id,
                'scheduled_date': self.ks_schedule_date,
                'move_ids': incoming_move_lines,
                'move_line_ids': incoming_move_line_ids,
                'origin': self.name,
                'location_dest_id': self.ks_transfer_to_location.id
            })
            ks_picking_to_id.action_assign()
            ext_move = self.env['stock.move.line'].search(
                [('picking_id', '=', ks_picking_to_id.id), ('ks_custom_line', '=', False)])
            ext_move.unlink()
            if not ks_picking_to_id.move_line_ids:
                for move_line, stock_line in zip(ks_picking_to_id.move_line_ids, self.ks_multicompany_transfer_stock_ids):
                    move_line.write({'quantity': stock_line.ks_reserved_availability})
            self.ks_update_lot_serial(ks_picking_to_id, self.ks_multicompany_transfer_stock_ids)
            ks_picking_to_id.button_validate()
            self.state = 'posted'
            self.ks_stock_picking_ids = [(6, 0, [ks_picking_from_id.id, ks_picking_to_id.id])]

        # For unlinking the unused quant
        self.env['stock.quant']._unlink_zero_quants()

    def ks_incoming_move_line(self, ks_multicompany_transfer_stock_ids):
        move_lines = []
        ks_location = self.env['stock.location'].sudo().with_company(self.ks_transfer_to).search([('usage', '=', 'transit')], order='company_id desc', limit=1)
        if not ks_location:
            self.env['stock.location'].sudo().with_company(self.ks_transfer_to).create({'name': _('Inter-warehouse transit'),
                                               'usage': 'transit',
                                               'company_id': False,
                                               'location_id': False})
        picking_incoming_id = self.env['stock.picking.type'].sudo().with_company(self.ks_transfer_to).search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', self.ks_transfer_to.id),
        ], limit=1)
        for rec in ks_multicompany_transfer_stock_ids:
            if rec.ks_product_id.tracking == 'serial':
                move_lines.append((0, 0, {
                    'name': rec.ks_product_id.name,
                    'product_id': rec.ks_product_id.id,
                    'product_uom_qty': rec.ks_qty_transfer,
                    'product_uom': rec.ks_product_uom_type.id,
                    'location_id': self.env['stock.location'].sudo().with_company(self.ks_transfer_to).search([('usage', '=', 'transit'), '|',
                                                                      ('company_id', '=', self.ks_transfer_to.id),
                                                                      ('company_id', '=', False),

                                                                      ], limit=1, order='company_id desc').id,
                    'location_dest_id': self.ks_transfer_to_location.id,
                    'picking_type_id': picking_incoming_id.id,
                    'company_id': self.ks_transfer_to.id,
                    'partner_id': self.ks_transfer_from.partner_id.id,
                }))
            elif rec.ks_product_id.tracking == 'lot' or rec.ks_product_id.tracking == 'none':
                move_lines.append((0, 0, {
                    'name': rec.ks_product_id.name,
                    'product_id': rec.ks_product_id.id,
                    'product_uom_qty': rec.ks_qty_transfer,
                    'product_uom': rec.ks_product_uom_type.id,
                    'location_id': self.env['stock.location'].sudo().with_company(self.ks_transfer_to).search([('usage', '=', 'transit'), '|',
                                                                      ('company_id', '=', self.ks_transfer_to.id),
                                                                      ('company_id', '=', False),

                                                                      ], limit=1, order='company_id desc').id,
                    'location_dest_id': self.ks_transfer_to_location.id,
                    'picking_type_id': picking_incoming_id.id,
                    'company_id': self.ks_transfer_to.id,
                    'partner_id': self.ks_transfer_from.partner_id.id,

                }))

        for move_line in move_lines:
            move_vals = move_line[2]  # The values dictionary is at index 2 in the tuple (0, 0, {values})
            move_vals.update({
                'is_multi_company_transfer': True,
                'source_company_id': self.ks_transfer_from.id,
                'dest_company_id': self.ks_transfer_to.id,
            })


        return move_lines

    def ks_incoming_move_line_ids(self, ks_multicompany_transfer_stock_ids):
        move_line_ids = []
        ks_location = self.env['stock.location'].sudo().search([('usage', '=', 'transit')], order='company_id desc', limit=1)
        if not ks_location:
            self.env['stock.location'].sudo().with_company(self.ks_transfer_from).create({'name': _('Inter-warehouse transit'),
                                               'usage': 'transit',
                                               'company_id': False,
                                               'location_id': False})

        for rec in ks_multicompany_transfer_stock_ids:
            for line in rec.ks_move_line_ids:
                if line.ks_product_id.tracking == 'lot':
                    move_line_ids.append((0, 0, {
                        'lot_name': line.ks_receiver_lot_id.name,
                        'product_id': line.ks_product_id.id,
                        'lot_id': line.ks_receiver_lot_id.id,
                        'quantity': line.ks_qty_done,
                        'product_uom_id': rec.ks_product_uom_type.id,
                        'location_id': ks_location.id,
                        'ks_custom_line': True,
                        'location_dest_id': line.ks_location_dest_id.id}))
                elif line.ks_product_id.tracking == 'serial':
                    move_line_ids.append((0, 0, {
                        'product_id': line.ks_product_id.id,
                        'quantity': line.ks_qty_done,
                        'product_uom_id': rec.ks_product_uom_type.id,
                        'location_id': ks_location.id,
                        'ks_custom_line': True,
                        'location_dest_id': line.ks_location_dest_id.id}))
                elif line.ks_product_id.tracking == 'none':
                    move_line_ids.append((0, 0, {
                        'product_id': line.ks_product_id.id,
                        'quantity': line.ks_qty_done,
                        'product_uom_id': rec.ks_product_uom_type.id,
                        'location_id': ks_location.id,
                        'ks_custom_line': True,
                        'location_dest_id': line.ks_location_dest_id.id}))

        return move_line_ids

    def ks_outgoing_move_line(self, ks_multicompany_transfer_stock_ids):
        move_lines = []
        ks_location = self.env['stock.location'].sudo().search([('usage', '=', 'transit')], order='company_id desc', limit=1)
        if not ks_location:
            self.env['stock.location'].sudo().with_company(self.ks_transfer_from).create({'name': _('Inter-warehouse transit'),
                                               'usage': 'transit',
                                               'company_id': False,
                                               'location_id': False})
        picking_type = self.env['stock.picking.type'].sudo().with_company(self.ks_transfer_from).search([
            ('code', '=', 'outgoing'),
            ('warehouse_id.company_id', '=', self.ks_transfer_from.id),
        ], limit=1)
        for rec in ks_multicompany_transfer_stock_ids:
            if rec.ks_product_id.tracking == 'serial':
                move_lines.append((0, 0, {
                    'name': rec.ks_product_id.name,
                    'product_id': rec.ks_product_id.id,
                    'product_uom_qty': rec.ks_qty_transfer,
                    'product_uom': rec.ks_product_uom_type.id,
                    'location_id': self.ks_transfer_from_location.id,
                    'location_dest_id': self.env['stock.location'].sudo().with_company(self.ks_transfer_from).search([('usage', '=', 'transit'), '|',
                                                                           (
                                                                               'company_id', '=',
                                                                               self.ks_transfer_from.id),
                                                                           ('company_id', '=', False),

                                                                           ], limit=1, order='company_id desc').id,

                    'picking_type_id': picking_type.id,
                    'company_id': self.ks_transfer_from.id,
                    'partner_id': self.ks_transfer_to.partner_id.id,
                    'ks_move_id': rec.id
                }))
            elif rec.ks_product_id.tracking == 'lot' or rec.ks_product_id.tracking == 'none':
                move_lines.append((0, 0, {
                    'name': rec.ks_product_id.name,
                    'product_id': rec.ks_product_id.id,
                    'product_uom_qty': rec.ks_qty_transfer,
                    'product_uom': rec.ks_product_uom_type.id,
                    'location_id': self.ks_transfer_from_location.id,
                    'location_dest_id': self.env['stock.location'].sudo().with_company(self.ks_transfer_from).search([('usage', '=', 'transit'), '|',
                                                                           (
                                                                               'company_id', '=',
                                                                               self.ks_transfer_from.id),
                                                                           ('company_id', '=', False),

                                                                           ], limit=1, order='company_id desc').id,

                    'picking_type_id': picking_type.id,
                    'company_id': self.ks_transfer_from.id,
                    'partner_id': self.ks_transfer_to.partner_id.id,
                    'ks_move_id': rec.id
                }))
        
        for move_line in move_lines:
            move_vals = move_line[2]  # The values dictionary is at index 2 in the tuple (0, 0, {values})
            move_vals.update({
                'is_multi_company_transfer': True,
                'source_company_id': self.ks_transfer_from.id,
                'dest_company_id': self.ks_transfer_to.id,
            })


        return move_lines

    def ks_outgoing_move_line_ids(self, ks_multicompany_transfer_stock_ids):
        move_line_ids = []
        ks_location = self.env['stock.location'].sudo().search([('usage', '=', 'transit')], order='company_id desc', limit=1)
        if not ks_location:
            self.env['stock.location'].sudo().with_company(self.ks_transfer_from).create({'name': _('Inter-warehouse transit'),
                                               'usage': 'transit',
                                               'company_id': False,
                                               'location_id': False})
        for rec in ks_multicompany_transfer_stock_ids:
            for line in rec.ks_move_line_ids:
                if not line.ks_qty_done:
                    raise ValidationError(_(f'Please set Done quantity for {line.ks_product_id.name}'))
                if line.ks_product_id.tracking == 'lot':
                    move_line_ids.append((0, 0, {
                        'product_id': line.ks_product_id.id,
                        'lot_id': line.ks_lot_id.id,
                        'quantity': line.ks_qty_done,
                        'product_uom_id': rec.ks_product_uom_type.id,
                        'location_id': line.ks_location_id.id,
                        'location_dest_id': ks_location.id,
                        'ks_custom_line': True
                    }))
                elif line.ks_product_id.tracking == 'serial':
                    move_line_ids.append((0, 0, {
                        'product_id': line.ks_product_id.id,
                        'quantity': line.ks_qty_done,
                        'product_uom_id': rec.ks_product_uom_type.id,
                        'location_id': line.ks_location_id.id,
                        'location_dest_id': ks_location.id,
                        'ks_custom_line': True
                    }))
                elif line.ks_product_id.tracking == 'none':
                    move_line_ids.append((0, 0, {
                        'product_id': line.ks_product_id.id,
                        'quantity': line.ks_qty_done,
                        'product_uom_id': rec.ks_product_uom_type.id,
                        'location_id': line.ks_location_id.id,
                        'location_dest_id': ks_location.id,
                        'ks_custom_line': True
                    }))
        return move_line_ids

    def ks_prepare_move_lines(self, ks_multicompany_transfer_stock_ids):
        # Prepare move lines and return move lines
        move_lines = []
        if self.ks_transfer_to.id == self.ks_transfer_from.id:
            for rec in ks_multicompany_transfer_stock_ids:
                if rec.ks_product_id.tracking == 'serial':
                    move_lines.append((0, 0, {
                        'name': rec.ks_product_id.name,
                        'product_id': rec.ks_product_id.id,
                        'product_uom_qty': rec.ks_qty_transfer,
                        'product_uom': rec.ks_product_uom_type.id,
                        'location_id': self.ks_transfer_from_location.id,
                        'location_dest_id': self.ks_transfer_to_location.id,
                    }))
                elif rec.ks_product_id.tracking == 'lot' or rec.ks_product_id.tracking == 'none':
                    move_lines.append((0, 0, {
                        'name': rec.ks_product_id.name,
                        'product_id': rec.ks_product_id.id,
                        'product_uom_qty': rec.ks_qty_transfer,
                        'product_uom': rec.ks_product_uom_type.id,
                        'location_id': self.ks_transfer_from_location.id,
                        'location_dest_id': self.ks_transfer_to_location.id,
                    }))
        else:
            ks_location = self.env['stock.location'].sudo().search([('usage', '=', 'transit')], order='company_id desc',
                                                            limit=1)
            if not ks_location:
                self.env['stock.location'].sudo().with_company(self.ks_transfer_from).create({'name': _('Inter-warehouse transit'),
                                                   'usage': 'transit',
                                                   'company_id': False,
                                                   'location_id': False})
            for rec in ks_multicompany_transfer_stock_ids:
                if rec.ks_product_id.tracking == 'serial':
                    move_lines.append((0, 0, {
                        'name': rec.ks_product_id.name,
                        'product_id': rec.ks_product_id.id,
                        'product_uom_qty': rec.ks_qty_transfer,
                        'product_uom': rec.ks_product_uom_type.id,
                        'location_id': self.ks_transfer_from_location.id,
                        'location_dest_id': self.env['stock.location'].sudo().with_company(self.ks_transfer_from).search([('usage', '=', 'transit'),
                                                                               (
                                                                                   'company_id', '=',
                                                                                   self.ks_transfer_from.id),

                                                                               ], limit=1, order='company_id desc').id,
                    }))
                elif rec.ks_product_id.tracking == 'lot' or rec.ks_product_id.tracking == 'none':
                    move_lines.append((0, 0, {
                        'name': rec.ks_product_id.name,
                        'product_id': rec.ks_product_id.id,
                        'product_uom_qty': rec.ks_qty_transfer,
                        'product_uom': rec.ks_product_uom_type.id,
                        'location_id': self.ks_transfer_from_location.id,
                        'location_dest_id': self.env['stock.location'].sudo().with_company(self.ks_transfer_from).search([('usage', '=', 'transit'), '|',
                                                                               (
                                                                                   'company_id', '=',
                                                                                   self.ks_transfer_from.id),
                                                                               ('company_id', '=', False),

                                                                               ], limit=1, order='company_id desc').id,
                    }))
        return move_lines

    def ks_update_lot_serial(self, picking_id, ks_stock_ids):
        for move_line, stock_line in zip(picking_id.move_ids, ks_stock_ids):
            for line, ks_line in zip(move_line.move_line_ids, stock_line.ks_move_line_ids):
                if line.product_id.tracking != 'none':
                    qty = ks_line.ks_qty_done
                    if len(move_line.move_line_ids) < len(stock_line.ks_move_line_ids):
                        qty = line.quantity_product_uom
                        if move_line.product_uom_qty > qty:
                            move_line.write({'product_uom_qty': qty})
                    line.write({'lot_id': ks_line.ks_lot_id.id, 'quantity': qty})
                    if not ks_line.ks_qty_done:
                        ks_line.write({'ks_qty_done': qty})
                elif line.product_id.tracking == 'none':
                    qty = ks_line.ks_qty_done
                    line.write({'quantity': qty})

    def ks_button_inventory_entries(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Inventory Transfer',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.ks_stock_picking_ids.ids)],
            'view_type': 'form',
            'target': 'current',
        }

    def ks_check_availability(self):
        ks_stock_moves = self.ks_multicompany_transfer_stock_ids
        ks_moves = self.mapped('ks_multicompany_transfer_stock_ids')
        for moves in ks_stock_moves:
            if moves in self.ks_multicompany_transfer_stock_ids:
                moves.ks_merge_same_move_lines(moves, self.ks_multicompany_transfer_stock_ids)
            ks_moves = self.mapped('ks_multicompany_transfer_stock_ids')
        for move in self.ks_multicompany_transfer_stock_ids:
            if not move.ks_qty_transfer:
                raise ValidationError(_("Product (%s) having 0 quantity to transfer.\n"
                                        "Please delete the line or add some quantity to transfer in it!!") % move.ks_product_id.display_name)
            if not move.ks_qty_available:
                raise ValidationError(
                    _("Quantity is not available for the product - (%s) in the selected source location .\n"
                      "Please delete the line or add some quantity in the stock to transfer!!") % move.ks_product_id.display_name)
            if move.ks_qty_available < move.ks_qty_transfer:
                raise ValidationError(
                    _("Available Quantity is less than the Trnasfer Quantity for the product - (%s) in the selected source location .\n"
                      "Please Update the transfer quantity equal to available quantity or Update the quantity in stock to transfer!!") % move.ks_product_id.display_name)

            if move.ks_product_id.tracking == 'serial':
                if move.ks_qty_transfer - int(move.ks_qty_transfer) > 0:
                    raise ValidationError(_("%s can not be process with float(%s) quantity in case of"
                                            " serial tracking. Check %s move line again and change quantity with Integer value." % (
                                                move.ks_product_id.name, move.ks_qty_transfer,
                                                move.ks_product_id.name)))

            if move.ks_qty_transfer < 0:
                raise ValidationError(
                    _("Quantity transfer for product (%s) can not be negative." % move.ks_product_id.display_name))

        if self.ks_transfer_from_location == self.ks_transfer_to_location:
            raise UserError(_('Selected source and destination locations are the same. '
                              'You can not transfer into the same location, change it and try again.'))
        if not ks_moves:
            raise UserError(_('Nothing to check the availability for.'))
        res = ks_moves.ks_action_assign()
        if res:
            self.state = 'in_progress'
        return True

    def ks_unreserve_move_lines(self):
        for picking in self:
            flag = picking.ks_multicompany_transfer_stock_ids.ks_do_unreserve_lines()
            if flag:
                picking.state = 'draft'

    def ks_unreserve_before_validate(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for stock_line in self.ks_multicompany_transfer_stock_ids:
            for ks_move_line in stock_line.ks_move_line_ids:
                ks_product_qty = ks_move_line.ks_product_uom_id._compute_quantity(ks_move_line.ks_product_uom_qty,
                                                                                  ks_move_line.ks_product_id.uom_id,
                                                                                  rounding_method='HALF-UP')
                if ks_move_line.ks_product_id.is_storable and not ks_move_line._should_bypass_reservation(
                        ks_move_line.ks_location_id) and not float_is_zero(ks_product_qty,
                                                                           precision_digits=precision):
                    try:
                        self.env['stock.quant']._update_reserved_quantity(ks_move_line.ks_product_id,
                                                                          ks_move_line.ks_location_id,
                                                                          quantity=-ks_product_qty,
                                                                          lot_id=ks_move_line.ks_lot_id, strict=True)
                    except UserError:
                        if ks_move_line.ks_lot_id:
                            self.env['stock.quant']._update_reserved_quantity(ks_move_line.ks_product_id,
                                                                              ks_move_line.ks_location_id,
                                                                              quantity=-ks_product_qty,
                                                                              lot_id=False, strict=True)
                        else:
                            raise
