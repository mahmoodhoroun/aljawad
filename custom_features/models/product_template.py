from odoo import models, fields, api, _
from odoo.osv import expression
from psycopg2.errors import ForeignKeyViolation
from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    description = fields.Text(string="Description", index=True, translate=True)
    stock_display = fields.Char(string="Stock Available", compute="_compute_stock_display")

    _sql_constraints = [
        ('barcode_unique', 'unique(barcode)', 'A product with this barcode already exists.'),
    ]

    def action_remove_duplicate_products(self):
        """Remove duplicate products based on default_code (internal reference) if they have zero stock."""
        cr = self.env.cr
        
        # Get all products with default_code and their stock quantities
        query = """
            WITH product_stock AS (
                SELECT 
                    pp.id as product_id,
                    pp.product_tmpl_id,
                    pp.default_code,
                    COALESCE(SUM(sq.quantity), 0) as total_qty,
                    COUNT(sm.id) as move_count
                FROM product_product pp
                LEFT JOIN stock_quant sq ON sq.product_id = pp.id
                LEFT JOIN stock_move sm ON sm.product_id = pp.id AND sm.state != 'cancel'
                WHERE pp.default_code IS NOT NULL
                GROUP BY pp.id, pp.product_tmpl_id, pp.default_code
            )
            SELECT 
                ps.*,
                pt.name,
                (SELECT COUNT(*) 
                 FROM product_product pp2 
                 WHERE pp2.product_tmpl_id = ps.product_tmpl_id) as variant_count
            FROM product_stock ps
            JOIN product_template pt ON pt.id = ps.product_tmpl_id
            ORDER BY ps.default_code, ps.product_id
        """
        cr.execute(query)
        products_data = cr.dictfetchall()
        
        seen_references = {}
        products_to_delete = []
        successfully_deleted = 0
        failed_products = []

        # Identify duplicates
        for prod in products_data:
            if prod['default_code'] in seen_references:
                if prod['total_qty'] == 0 and prod['move_count'] == 0:
                    products_to_delete.append(prod)
            else:
                seen_references[prod['default_code']] = prod

        # Try to delete products one by one
        for prod in products_to_delete:
            try:
                # Delete product variant
                cr.execute("""
                    DELETE FROM product_product 
                    WHERE id = %s AND NOT EXISTS (
                        SELECT 1 FROM stock_move 
                        WHERE product_id = %s AND state != 'cancel'
                    )
                    RETURNING product_tmpl_id
                """, (prod['product_id'], prod['product_id']))
                
                deleted = cr.fetchone()
                if deleted:
                    # If this was the last variant, delete the template too
                    if prod['variant_count'] == 1:
                        cr.execute("""
                            DELETE FROM product_template 
                            WHERE id = %s
                        """, (prod['product_tmpl_id'],))
                    
                    successfully_deleted += 1
                else:
                    failed_products.append(prod)
                    
            except Exception as e:
                self.env.cr.rollback()  # Rollback on error
                failed_products.append(prod)
                continue

        # Commit the transaction
        self.env.cr.commit()

        # Prepare the message
        message = f'تم حذف {successfully_deleted} من المنتجات المكررة بنجاح\n'
        if failed_products:
            message += '\nالمنتجات التي لم يتم حذفها بسبب وجود حركات مخزون مرتبطة:\n'
            for prod in failed_products:
                message += f'- {prod["name"]} (رمز: {prod["default_code"]})\n'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'تم التنفيذ',
                'message': message,
                'type': 'warning' if failed_products else 'success',
                'sticky': True if failed_products else False,
            }
        }

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """ Custom search to allow intermittent search in description """
        new_domain = []
        
        for condition in domain:
            if isinstance(condition, (list, tuple)) and condition[0] == 'description':
                field, operator, value = condition
                if operator in ('ilike', '=like', 'like'):
                    words = value.split()
                    if words:
                        # Generate partial search domain using OR for better matching
                        search_conditions = []
                        for word in words:
                            search_conditions.append(('description', 'ilike', f"%{word}%"))
                        if len(search_conditions) > 1:
                            # Multiple words: use OR conditions
                            new_domain.append('|')
                            new_domain.extend(search_conditions[:-1])
                            new_domain.append(search_conditions[-1])
                        else:
                            # Single word: just add the condition
                            new_domain.append(search_conditions[0])
                        continue
            
            new_domain.append(condition)

        return super()._search(new_domain, offset=offset, limit=limit, order=order)

    @api.model
    def create(self, vals):
        # Check if user has the restricted group and prevent creation
        if self.env.user.has_group('custom_features.group_restrict_product_creation'):
            raise UserError(_('You do not have permission to create products. Please contact your administrator.'))

        # Check if this is a quick create from sale order or invoice
        # if self._context.get('quick_create_view') and vals.get('name') and not vals.get('default_code'):
            # Set default_code same as name only if it's not provided
        if not self._context.get('import_file'):
            vals['default_code'] = vals['name']

        vals['is_storable'] = True

        # Auto-generate barcode from category serial if category is selected and barcode is not provided
        if vals.get('categ_id') and not vals.get('barcode'):
            category = self.env['product.category'].browse(vals['categ_id'])
            if category:
                next_serial = category.get_next_serial()
                vals['barcode'] = str(next_serial)

        # Check if product with same reference already exists
        # if vals.get('barcode'):
        #     existing_product = self.env['product.template'].search([('barcode', '=', vals['barcode'])], limit=1)
        #     if existing_product:
        #         raise ValidationError(_('A product with barcode %s already exists. Please use the existing product or choose a different barcode.') % vals['barcode'])

        # if vals.get('type') == 'consu':
        #     print("Setting is_storable to True")
        #     print("**********************************************************")
        #     vals['is_storable'] = True
        return super(ProductTemplate, self).create(vals)

    def write(self, vals):
        # Auto-generate barcode from category serial if category is changed and barcode is not provided
        # if vals.get('categ_id') and not vals.get('barcode'):
        #     for record in self:
        #         if not record.barcode:  # Only if current record doesn't have a barcode
        #             category = self.env['product.category'].browse(vals['categ_id'])
        #             if category:
        #                 next_serial = category.get_next_serial()
        #                 vals['barcode'] = str(next_serial)
        #                 break  # Only set for the first record to avoid multiple increments

        # if vals.get('barcode'):
        #     existing_product = self.env['product.template'].search([('barcode', '=', vals['barcode'])], limit=1)
        #     if existing_product:
        #         raise ValidationError(_('A product with barcode %s already exists. Please use the existing product or choose a different barcode.') % vals['barcode'])
        return super(ProductTemplate, self).write(vals)
    
    # @api.onchange('categ_id')
    # def _onchange_categ_id(self):
    #     for record in self:
    #         if record.categ_id:
    #            next_serial = record.categ_id.get_next_serial()
    #            record.barcode = str(next_serial)
    
    @api.depends('name', 'default_code', 'categ_id.name', 'standard_price')
    def _compute_display_name(self):
        for template in self:
            if not template.name:
                template.display_name = False
                continue

            parts = []
            if template.default_code:
                parts.append(f"[{template.default_code}]")
            parts.append(template.name)
            if template.categ_id:
                parts.append(f"- [{template.categ_id.name}]")

            if template.stock_display:
                parts.append(f"({template.stock_display})")
            
            if template.barcode:
                parts.append(f"({template.barcode})")
                
            # Add cost information
            # if template.standard_price:
            #     parts.append(f"Cost: {template.standard_price:.2f}RS")
                
            template.display_name = ' '.join(parts)

    @api.depends('qty_available')
    def _compute_stock_display(self):
        """ Compute stock display format: main_warehouse_qty(total_warehouses_qty)
            main_warehouse_qty: sum of quantities in all internal locations under main warehouse
            total_warehouses_qty: sum of quantities in all internal locations under all allowed warehouses
        """
        user = self.env.user
        allowed_warehouses = user.allowed_warehouse_ids or self.env['stock.warehouse'].sudo().search([])
        
        # Get main warehouse (first from allowed warehouses or first overall if none allowed)
        main_warehouse = allowed_warehouses[0] if allowed_warehouses else self.env['stock.warehouse'].sudo().search([], limit=1)

        # Get all internal locations under main warehouse
        main_warehouse_locations = self.env['stock.location'].sudo().search([
            ('id', 'child_of', main_warehouse.view_location_id.id),
            ('usage', '=', 'internal')
        ])

        # Get all internal locations under all allowed warehouses
        all_warehouse_locations = self.env['stock.location'].sudo().search([
            ('id', 'child_of', allowed_warehouses.mapped('view_location_id').ids),
            ('usage', '=', 'internal')
        ])

        for product in self:
            # Calculate quantities using read_group to get quantities by location
            domain = [('product_id', 'in', product.product_variant_ids.ids)]
            
            # Main warehouse quantity
            main_domain = domain + [('location_id', 'in', main_warehouse_locations.ids)]
            main_qty_data = self.env['stock.quant'].sudo().read_group(
                main_domain, ['quantity:sum'], []
            )
            main_qty = main_qty_data[0]['quantity'] if main_qty_data and main_qty_data[0]['quantity'] else 0
            
            # Total warehouses quantity
            total_domain = domain + [('location_id', 'in', all_warehouse_locations.ids)]
            total_qty_data = self.env['stock.quant'].sudo().read_group(
                total_domain, ['quantity:sum'], []
            )
            total_qty = total_qty_data[0]['quantity'] if total_qty_data and total_qty_data[0]['quantity'] else 0

            # Format the display string as integers without decimal places, matching sale_order_line format
            product.stock_display = f"{int(main_qty)}({int(total_qty)})"



class ProductProduct(models.Model):
    _inherit = 'product.product'

    stock_display = fields.Char(string='Stock Display', compute='_compute_stock_display')

    @api.model
    def create(self, vals):
        # Check if user has the restricted group and prevent creation
        if self.env.user.has_group('custom_features.group_restrict_product_creation'):
            raise UserError(_('You do not have permission to create products. Please contact your administrator.'))
        return super(ProductProduct, self).create(vals)

    @api.depends('qty_available', 'stock_quant_ids')
    def _compute_stock_display(self):
        for product in self:
            product.stock_display = product.product_tmpl_id.stock_display



    @api.depends('name', 'default_code', 'categ_id.name', 'standard_price')
    def _compute_display_name(self):

        for product in self:
            if not product.name:
                product.display_name = False
                continue

            parts = []
            if product.default_code:
                parts.append(f"[{product.default_code}]")
            parts.append(product.name)
            if product.categ_id:
                parts.append(f"- [{product.categ_id.name}]")

            if product.stock_display:
                parts.append(f"({product.stock_display})")
                
            # Add cost information
            # if product.standard_price:
            #     parts.append(f"Cost: {product.standard_price:.2f}RS")
                
            product.display_name = ' '.join(parts)
