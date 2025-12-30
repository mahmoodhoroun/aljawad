# -*- coding: utf-8 -*-
from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Note: company_min_qty, company_max_qty, branch_min_qty, branch_max_qty
    # are already defined on product.template and inherited automatically
    # No need to redefine them here

    def get_effective_min_max(self):
        """
        Get effective min/max values for the current company.
        Returns dict with company_min, company_max, branch_min, branch_max.
        Inherits from parent company if values are not set.

        If 'branch_company_id' is in context, uses that company instead of env.company
        """
        self.ensure_one()

        # Check if a specific branch company is requested via context
        branch_company_id = self.env.context.get('branch_company_id')
        if branch_company_id:
            # Use the specified branch company
            current_company = self.env['res.company'].browse(branch_company_id)
            product_in_branch = self.with_company(current_company)
        else:
            # Use the current environment company
            current_company = self.env.company
            product_in_branch = self

        # Get values for the target company via the template
        result = {
            'company_min': product_in_branch.product_tmpl_id.company_min_qty,
            'company_max': product_in_branch.product_tmpl_id.company_max_qty,
            'branch_min': product_in_branch.product_tmpl_id.branch_min_qty,
            'branch_max': product_in_branch.product_tmpl_id.branch_max_qty,
        }

        # If current company has a parent and values are not set, inherit from parent
        if current_company.parent_id:
            product_in_parent_tmpl = self.product_tmpl_id.with_company(current_company.parent_id)

            if not result['company_min']:
                result['company_min'] = product_in_parent_tmpl.company_min_qty
            if not result['company_max']:
                result['company_max'] = product_in_parent_tmpl.company_max_qty
            if not result['branch_min']:
                result['branch_min'] = product_in_parent_tmpl.branch_min_qty
            if not result['branch_max']:
                result['branch_max'] = product_in_parent_tmpl.branch_max_qty

        return result
