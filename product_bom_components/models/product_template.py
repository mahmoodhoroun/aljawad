from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    bom_component_ids = fields.One2many(
        'product.bom.component',
        'product_tmpl_id',
        string='BoM Components',
        help='Components from the Bill of Materials. Changes here sync with BoM.'
    )

    def action_load_bom_components(self):
        """Load BoM components into the product form"""
        for product in self:
            # Check if MRP module is installed
            if 'mrp.bom' not in self.env:
                raise UserError('Manufacturing module (MRP) is not installed. Please install it to use this feature.')

            # Find the main BoM for this product
            bom = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', product.id),
                ('product_id', '=', False),
            ], limit=1, order='id asc')

            if bom:
                # Delete existing component records WITHOUT syncing to BoM
                # (we're loading FROM the BoM, so we don't want to delete BoM lines)
                product.bom_component_ids.with_context(skip_bom_sync=True).unlink()

                # Create component records from BoM lines (also skip sync since they already exist in BoM)
                for line in bom.bom_line_ids:
                    self.env['product.bom.component'].with_context(skip_bom_sync=True).create({
                        'product_tmpl_id': product.id,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_qty,
                        'product_uom_id': line.product_uom_id.id,
                        'bom_line_id': line.id,
                        'sequence': line.sequence,
                    })
            else:
                raise UserError('No Bill of Materials found for this product.')
