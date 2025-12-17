from odoo import api, fields, models
from odoo.tools import float_compare
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warehouse_ids = fields.One2many('order.line.warehouse', 'so_line_id', string="Order Line Warehouse Configuration",
                                    compute="_compute_warehouse_ids_lines", store=True, readonly=False)

    def _is_auto_select_warehouse_qty(self):
        return self.env['ir.config_parameter'].sudo().get_param('sale.auto_select_warehouse_qty')

    def _get_allowed_warehouses(self):
        """Get warehouses that user has access to based on allowed warehouses and company access"""
        user = self.env.user
        # Get user's allowed warehouses
        allowed_warehouses = user.allowed_warehouse_ids
        
        # If no specific warehouses are allowed, get all warehouses from companies user has access to
        if not allowed_warehouses:
            allowed_warehouses = self.env['stock.warehouse'].sudo().search([])
        
        return allowed_warehouses

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_warehouse_ids_lines(self):
        if self._is_auto_select_warehouse_qty():
            for so_line in self:
                warehouse_line = []
                order = so_line.order_id
                default_warehouse = order.warehouse_id
                
                # Get allowed warehouses
                warehouse_ids = self._get_allowed_warehouses()
                
                # Ensure default warehouse is allowed
                if default_warehouse and default_warehouse not in warehouse_ids:
                    default_warehouse = False

                # first check quantity is available in the default warehouse and set it to the warehouse_ids
                need = so_line.product_uom_qty
                if default_warehouse:
                    available_qty = so_line.product_id.with_context(warehouse_id=default_warehouse.id).qty_available
                    if available_qty:
                        if available_qty >= need:
                            warehouse_line.append((0, 0, {'warehouse_id': default_warehouse.id, 'qty': need}))
                            need = 0
                        else:
                            warehouse_line.append((0, 0, {'warehouse_id': default_warehouse.id, 'qty': available_qty}))
                            need = need - available_qty
                if need:
                    # if still some quantity is remaining then check in other warehouses and set it to the warehouse_ids
                    for warehouse in warehouse_ids:
                        if warehouse == default_warehouse:
                            continue
                        available_qty = so_line.product_id.with_context(warehouse=warehouse.id).qty_available
                        if available_qty:
                            if available_qty >= need:
                                warehouse_line.append((0, 0, {'warehouse_id': warehouse.id, 'qty': need}))
                                need = 0
                            else:
                                warehouse_line.append((0, 0, {'warehouse_id': warehouse.id, 'qty': available_qty}))
                                need = need - available_qty
                        if not need:
                            break
                if so_line.warehouse_ids:
                    so_line.warehouse_ids.unlink()
                so_line.warehouse_ids = warehouse_line
        else:
            for so_line in self:
                warehouse_line = []
                if so_line.warehouse_ids:
                    so_line.warehouse_ids.unlink()
                # Get allowed warehouses
                warehouse_ids = self._get_allowed_warehouses()
                for warehouse in warehouse_ids:
                    warehouse_line.append((0, 0, {'warehouse_id': warehouse.id, 'qty': 0}))
                so_line.warehouse_ids = warehouse_line

    def _prepare_procurement_values(self, group_id=False):
        """Override to add proper route_ids"""
        values = super()._prepare_procurement_values(group_id=group_id)
        
        # Get the default route for warehouse deliveries
        picking_type_out = self.env.ref('stock.picking_type_out')
        warehouse_route = self.env['stock.route'].sudo().search([
            ('rule_ids.picking_type_id', '=', picking_type_out.id),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.order_id.company_id.id)
        ], limit=1)
        
        if warehouse_route:
            values['route_ids'] = warehouse_route
            
        return values

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        if self._context.get("skip_procurement"):
            return True
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.state != 'sale' or not line.product_id.type in ('consu', 'product'):
                continue
            qty = line._get_qty_procurement(previous_product_uom_qty)
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) == 0:
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({'move_type': line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            for warehouse in line.warehouse_ids:
                # Create procurement with sudo to bypass company restrictions
                values = line.sudo()._prepare_procurement_values(group_id=group_id)
                warehouse_company = self.env['res.company'].sudo().browse(warehouse.warehouse_id.company_id.id)
                
                # Get warehouse-specific outgoing picking type
                picking_type_out = warehouse.warehouse_id.sudo().out_type_id
                
                # Get warehouse-specific route
                warehouse_route = self.env['stock.route'].sudo().search([
                    ('rule_ids.picking_type_id', '=', picking_type_out.id),
                    '|',
                    ('company_id', '=', False),
                    ('company_id', '=', warehouse_company.id)
                ], limit=1)
                
                if not warehouse_route:
                    # Create a new route if none exists
                    warehouse_route = self.env['stock.route'].sudo().create({
                        'name': f'Delivery Route for {warehouse.warehouse_id.name}',
                        'product_selectable': True,
                        'company_id': warehouse_company.id,
                    })
                    
                    # Create pull rule
                    self.env['stock.rule'].sudo().create({
                        'name': f'Delivery Rule for {warehouse.warehouse_id.name}',
                        'action': 'pull',
                        'picking_type_id': picking_type_out.id,
                        'location_src_id': warehouse.warehouse_id.lot_stock_id.id,
                        'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                        'route_id': warehouse_route.id,
                        'company_id': warehouse_company.id,
                    })
                
                values.update({
                    'warehouse_id': warehouse.warehouse_id,
                    'company_id': warehouse_company,
                    'route_ids': warehouse_route,
                    'picking_type_id': picking_type_out.id,
                })
                
                product_qty = warehouse.qty
                line_uom = line.product_uom
                quant_uom = line.product_id.uom_id
                product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
                
                # Create procurement with sudo to allow delivery from any company
                procurement = self.env['procurement.group'].sudo().Procurement(
                    line.product_id, product_qty, procurement_uom,
                    line.order_id.partner_shipping_id.property_stock_customer,
                    line.name, line.order_id.name, warehouse_company, values)
                procurements.append(procurement)

            remaining_qty = line.product_uom_qty - sum(line.warehouse_ids.mapped('qty'))
            if remaining_qty > 0:
                values = line._prepare_procurement_values(group_id=group_id)
                product_qty = remaining_qty
                line_uom = line.product_uom
                quant_uom = line.product_id.uom_id
                product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
                procurements.append(self.env['procurement.group'].Procurement(
                    line.product_id, product_qty, procurement_uom,
                    line.order_id.partner_shipping_id.property_stock_customer,
                    line.name, line.order_id.name, line.order_id.company_id, values))

        if procurements:
            self.env['procurement.group'].sudo().run(procurements)

        # This next block is currently needed only because the scheduler trigger is done by picking confirmation rather than stock.move confirmation
        orders = self.mapped('order_id')
        for order in orders:
            pickings_to_confirm = order.picking_ids.filtered(lambda p: p.state not in ['cancel', 'done'])
            if pickings_to_confirm:
                # Trigger the Scheduler for Pickings with sudo to confirm pickings from any company
                pickings_to_confirm.sudo().action_confirm()
        return True

    def select_warehouse_quantity_wizard(self):
        wizard_id = self.env.ref('warehouse_selector_sale_orders.sale_order_line_warehouse_selection_view').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'view_type': 'form',
            'view_id': wizard_id,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            "context": {"create": False},
        }

    def close_action_window(self):
        return True
