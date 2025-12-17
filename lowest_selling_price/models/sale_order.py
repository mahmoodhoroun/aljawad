from odoo import models, api, _ , fields
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    lowest_selling_price = fields.Boolean(string='Lowest Selling Price')
    allow_sell_bellow_cost = fields.Boolean(string='Allow Sell bellow Cost')
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', help="Total cost.")
    net_profit = fields.Float(string='Net Profit', compute='_compute_net_profit', help="Net profit (Total Price - Total Cost).")
    
    show_total_cost_net_profit = fields.Boolean()

    @api.depends('order_line', 'order_line.product_id', 'order_line.product_uom_qty')
    def _compute_total_cost(self):
        for order in self:
            total = 0.0
            for line in order.order_line:
                total += line.product_id.standard_price * line.product_uom_qty
            order.total_cost = total
    
    @api.depends('amount_total', 'total_cost', 'amount_discount', 'amount_tax')
    def _compute_net_profit(self):
        for order in self:
            order.net_profit = order.amount_total - order.total_cost - order.amount_discount - order.amount_tax
    
    @api.model
    def default_get(self, fields_list):
        defaults = super(SaleOrder, self).default_get(fields_list)
        if 'lowest_selling_price' in fields_list:
            param_value = self.env['ir.config_parameter'].sudo().get_param('lowest_selling_price.lowest_selling_price') == 'True'
            param_value2 = self.env['ir.config_parameter'].sudo().get_param('lowest_selling_price.allow_sell_bellow_cost') == 'True'
            defaults['lowest_selling_price'] = param_value
            defaults['allow_sell_bellow_cost'] = param_value2
        return defaults
    

    def write(self, vals):
        result = super(SaleOrder, self).write(vals)
        if vals.get('state') == 'sale':
            self.check_lowest_price_permission()
        return result

    def action_confirm(self):
        return super(SaleOrder, self).action_confirm()

    def check_lowest_price_permission(self):
        self.ensure_one()
        if self.state not in ['draft', 'sent']:
            return True
        unauthorized_lines = []
        warning_lines = []
        unauthorized_lines2 = []
        warning_lines2 = []


        
        if self.lowest_selling_price and not self.allow_sell_bellow_cost:
            for line in self.order_line:
                if line.price_unit < line.lowest_price:
                    if self.env.user.has_group('lowest_selling_price.group_allow_lower_price'):
                        warning_lines.append(f"{line.product_id.display_name} ({line.price_unit} < {line.lowest_price})")
                    else:
                        unauthorized_lines.append(f"{line.product_id.display_name} ({line.price_unit} < {line.lowest_price})")

            if unauthorized_lines:
                raise UserError(_("You are not allowed to confirm this order because the following products are below cost:\n\n- " + "\n- ".join(unauthorized_lines)))

            if warning_lines:
                return {
                    'name': _('Confirm Low Price'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'confirm.low.price.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_sale_order_id': self.id,
                        'default_text': _('Some products are below the allowed price:\n\n- %s') % '\n- '.join(warning_lines)
                    }
                }
            
            return self.action_confirm()
            
        if self.allow_sell_bellow_cost and not self.lowest_selling_price:
            
            for line in self.order_line:
                 if line.price_unit < line.product_id.standard_price:
                    if self.env.user.has_group('lowest_selling_price.group_allow_sell_bellow_cost'):
                        warning_lines2.append(f"{line.product_id.display_name} ({line.price_unit} < {line.product_id.standard_price})")
                    else:
                        unauthorized_lines2.append(f"{line.product_id.display_name} ({line.price_unit} < {line.product_id.standard_price})")
            
            if unauthorized_lines2:
                raise UserError(_("You are not allowed to confirm this order because the following products are below cost:\n\n- " + "\n- ".join(unauthorized_lines2)))
            
            if warning_lines2:
                return {
                    'name': _('Confirm Low Cost'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'confirm.low.price.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_sale_order_id': self.id,
                        'default_text': _('Some products are below the allowed price:\n\n- %s') % '\n- '.join(warning_lines2)
                    }
                }
            else:
                return self.action_confirm()

        if self.allow_sell_bellow_cost and self.lowest_selling_price:
            for line in self.order_line:
                if line.price_unit < line.lowest_price:
                    if self.env.user.has_group('lowest_selling_price.group_allow_lower_price'):
                        warning_lines.append(f"{line.product_id.display_name} ({line.price_unit} < {line.lowest_price})")
                    else:
                        unauthorized_lines.append(f"{line.product_id.display_name} ({line.price_unit} < {line.lowest_price})")
                
            for line in self.order_line:
                if line.price_unit < line.product_id.standard_price:
                    if self.env.user.has_group('lowest_selling_price.group_allow_sell_bellow_cost'):
                        warning_lines2.append(f"{line.product_id.display_name} ({line.price_unit} < {line.product_id.standard_price})")
                    else:
                        unauthorized_lines2.append(f"{line.product_id.display_name} ({line.price_unit} < {line.product_id.standard_price})")
            _logger.info("-*********************************************************")
            _logger.info(unauthorized_lines)
            _logger.info(unauthorized_lines2)
            _logger.info(warning_lines)
            _logger.info(warning_lines2)

            if unauthorized_lines:
                raise UserError(_("You are not allowed to confirm this order because the following products are below lowest price:\n\n- " + "\n- ".join(unauthorized_lines)))

            elif unauthorized_lines2:
                raise UserError(_("You are not allowed to confirm this order because the following products are below cost price:\n\n- " + "\n- ".join(unauthorized_lines2)))

            elif warning_lines and not warning_lines2:
                return {
                    'name': _('Confirm Low Price'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'confirm.low.price.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_sale_order_id': self.id,
                        'default_text': _('Some products are below the allowed price:\n\n- %s') % '\n- '.join(warning_lines)
                    }
                }
            elif warning_lines2 and not warning_lines:
                return {
                    'name': _('Confirm Low Cost'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'confirm.low.price.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_sale_order_id': self.id,
                        'default_text': _('Some products are below the allowed price:\n\n- %s') % '\n- '.join(warning_lines2)
                    }
                }
            elif warning_lines and warning_lines2:
                return {
                    'name': _('Confirm Low Price and Cost'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'confirm.low.price.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_sale_order_id': self.id,
                        'default_text': _('Some products are below the allowed price:\n\n- %s') % '\n- '.join(warning_lines + warning_lines2)
                    }
                }
            else:
                return self.action_confirm()

            
            

                
            

    @api.onchange('order_line', 'order_line.price_unit')
    def _onchange_check_lowest_price(self):
        warning_lines = []
        for line in self.order_line:
            if line.price_unit < line.lowest_price and self.env.user.has_group('lowest_selling_price.group_allow_lower_price'):
                warning_lines.append(f"{line.product_id.display_name} ({line.price_unit} < {line.lowest_price})")
        
        if warning_lines:
            return {
                'warning': {
                    'title': _("Warning for Price"),
                    'message': _("Some products are below the allowed price:\n\n- %s") % "\n- ".join(warning_lines)
                }
            }


    def show_hide_total_cost(self):
        if self.show_total_cost_net_profit:
            self.show_total_cost_net_profit = False
        else:
            self.show_total_cost_net_profit = True
