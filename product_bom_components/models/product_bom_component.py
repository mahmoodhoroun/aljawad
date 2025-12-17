from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductBomComponent(models.Model):
    _name = 'product.bom.component'
    _description = 'Product BoM Component (Synced with BoM)'
    _rec_name = 'product_id'

    product_tmpl_id = fields.Many2one('product.template', string='Product', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Component', required=True)
    product_qty = fields.Float(string='Quantity', default=1.0, required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    bom_line_id = fields.Integer(string='BoM Line ID', readonly=True, help='Reference to mrp.bom.line ID')
    sequence = fields.Integer(string='Sequence', default=10)

    def _is_mrp_installed(self):
        """Check if MRP module is installed"""
        return 'mrp.bom' in self.env

    @api.model
    def create(self, vals):
        """When creating a component, also create it in the BoM"""
        # Auto-fill UoM if not provided
        if 'product_id' in vals and not vals.get('product_uom_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            if product and product.uom_id:
                vals['product_uom_id'] = product.uom_id.id

        component = super(ProductBomComponent, self).create(vals)

        # Skip sync if we're loading from BoM (components already exist in BoM)
        if not self.env.context.get('skip_bom_sync'):
            component._sync_to_bom('create')
        return component

    def write(self, vals):
        """When updating a component, also update it in the BoM"""
        result = super(ProductBomComponent, self).write(vals)
        for component in self:
            component._sync_to_bom('write')
        return result

    def unlink(self):
        """When deleting a component, also delete it from the BoM"""
        # Skip sync if we're loading from BoM (to avoid deleting BoM lines we're about to reload)
        if not self.env.context.get('skip_bom_sync'):
            for component in self:
                component._sync_to_bom('unlink')
        return super(ProductBomComponent, self).unlink()

    def _sync_to_bom(self, operation):
        """Sync changes to the BoM (only if MRP module is installed)"""
        self.ensure_one()

        # Skip if MRP module is not installed
        if not self._is_mrp_installed():
            return

        # Find the main BoM for this product
        bom = self.env['mrp.bom'].search([
            ('product_tmpl_id', '=', self.product_tmpl_id.id),
            ('product_id', '=', False),  # Template BoM, not variant-specific
        ], limit=1, order='id asc')  # Get the first/main BoM

        if not bom and operation != 'unlink':
            # No BoM exists, create one
            bom = self.env['mrp.bom'].create({
                'product_tmpl_id': self.product_tmpl_id.id,
                'product_qty': 1.0,
                'type': 'normal',
            })

        if operation == 'create':
            # Create new BoM line (skip reverse sync to avoid infinite loop)
            bom_line = self.env['mrp.bom.line'].with_context(skip_bom_sync=True).create({
                'bom_id': bom.id,
                'product_id': self.product_id.id,
                'product_qty': self.product_qty,
                'product_uom_id': self.product_uom_id.id,
                'sequence': self.sequence,
            })
            # Link the BoM line to this component
            self.write({'bom_line_id': bom_line.id})

        elif operation == 'write':
            # Update existing BoM line (skip reverse sync to avoid infinite loop)
            if self.bom_line_id:
                bom_line = self.env['mrp.bom.line'].browse(self.bom_line_id)
                if bom_line.exists():
                    bom_line.with_context(skip_bom_sync=True).write({
                        'product_id': self.product_id.id,
                        'product_qty': self.product_qty,
                        'product_uom_id': self.product_uom_id.id,
                        'sequence': self.sequence,
                    })

        elif operation == 'unlink':
            # Delete BoM line (skip reverse sync to avoid infinite loop)
            if self.bom_line_id:
                bom_line = self.env['mrp.bom.line'].browse(self.bom_line_id)
                if bom_line.exists():
                    bom_line.with_context(skip_bom_sync=True).unlink()

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-fill UoM when product is selected"""
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    @api.model
    def create(self, vals):
        """When creating a BoM line, also create/update it in product components"""
        line = super(MrpBomLine, self).create(vals)

        # Skip reverse sync if we're syncing FROM product components
        if not self.env.context.get('skip_bom_sync'):
            line._sync_to_product_components('create')
        return line

    def write(self, vals):
        """When updating a BoM line, also update it in product components"""
        result = super(MrpBomLine, self).write(vals)

        # Skip reverse sync if we're syncing FROM product components
        if not self.env.context.get('skip_bom_sync'):
            for line in self:
                line._sync_to_product_components('write')
        return result

    def unlink(self):
        """When deleting a BoM line, also delete it from product components"""
        # Skip reverse sync if we're syncing FROM product components
        if not self.env.context.get('skip_bom_sync'):
            for line in self:
                line._sync_to_product_components('unlink')
        return super(MrpBomLine, self).unlink()

    def _sync_to_product_components(self, operation):
        """Sync BoM line changes to product components"""
        self.ensure_one()

        # Only sync for template-level BoMs (not variant-specific)
        if self.bom_id.product_id:
            return

        product_tmpl = self.bom_id.product_tmpl_id
        if not product_tmpl:
            return

        if operation == 'create':
            # Create new component record
            self.env['product.bom.component'].with_context(skip_bom_sync=True).create({
                'product_tmpl_id': product_tmpl.id,
                'product_id': self.product_id.id,
                'product_qty': self.product_qty,
                'product_uom_id': self.product_uom_id.id,
                'bom_line_id': self.id,
                'sequence': self.sequence,
            })

        elif operation == 'write':
            # Find and update existing component record
            component = self.env['product.bom.component'].search([
                ('bom_line_id', '=', self.id),
                ('product_tmpl_id', '=', product_tmpl.id),
            ], limit=1)

            if component:
                component.with_context(skip_bom_sync=True).write({
                    'product_id': self.product_id.id,
                    'product_qty': self.product_qty,
                    'product_uom_id': self.product_uom_id.id,
                    'sequence': self.sequence,
                })

        elif operation == 'unlink':
            # Find and delete component record
            component = self.env['product.bom.component'].search([
                ('bom_line_id', '=', self.id),
                ('product_tmpl_id', '=', product_tmpl.id),
            ], limit=1)

            if component:
                component.with_context(skip_bom_sync=True).unlink()
