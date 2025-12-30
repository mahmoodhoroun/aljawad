# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Company Min/Max (Global - one value per company)
    company_min_qty = fields.Float(
        string='Company Min',
        company_dependent=False,
        digits='Product Unit of Measure',
        help='Minimum quantity for this product at company level. '
             'This value is shared across all branches in the company.'
    )
    company_max_qty = fields.Float(
        string='Company Max',
        company_dependent=False,
        digits='Product Unit of Measure',
        help='Maximum quantity for this product at company level. '
             'This value is shared across all branches in the company.'
    )

    # Branch Min/Max (Per location AND per company)
    # These are also company_dependent so each company has its own branch values
    branch_min_qty = fields.Float(
        string='Branch Min',
        company_dependent=True,
        digits='Product Unit of Measure',
        help='Minimum quantity for this product at branch/location level. '
             'This value is specific to each branch within this company.'
    )
    branch_max_qty = fields.Float(
        string='Branch Max',
        company_dependent=True,
        digits='Product Unit of Measure',
        help='Maximum quantity for this product at branch/location level. '
             'This value is specific to each branch within this company.'
    )

    # Display fields that show inherited values from parent company
    display_company_min_qty = fields.Float(
        string='Company Min (Display)',
        compute='_compute_display_min_max',
        digits='Product Unit of Measure',
        help='Displays company min, inherited from parent company if not set.'
    )
    display_company_max_qty = fields.Float(
        string='Company Max (Display)',
        compute='_compute_display_min_max',
        digits='Product Unit of Measure',
        help='Displays company max, inherited from parent company if not set.'
    )
    display_branch_min_qty = fields.Float(
        string='Branch Min (Display)',
        compute='_compute_display_min_max',
        digits='Product Unit of Measure',
        help='Displays branch min, inherited from parent company if not set.'
    )
    display_branch_max_qty = fields.Float(
        string='Branch Max (Display)',
        compute='_compute_display_min_max',
        digits='Product Unit of Measure',
        help='Displays branch max, inherited from parent company if not set.'
    )

    @api.depends('company_min_qty', 'company_max_qty', 'branch_min_qty', 'branch_max_qty')
    def _compute_display_min_max(self):
        """Compute display values that inherit from parent company if not set."""
        for product in self:
            current_company = self.env.company

            # Get values for current company
            company_min = product.company_min_qty
            company_max = product.company_max_qty
            branch_min = product.branch_min_qty
            branch_max = product.branch_max_qty

            # If current company has a parent and values are not set, try to inherit from parent
            if current_company.parent_id:
                # Switch context to parent company to get parent values
                product_in_parent = product.with_company(current_company.parent_id)

                # Inherit company min/max from parent if not set
                if not company_min:
                    company_min = product_in_parent.company_min_qty
                if not company_max:
                    company_max = product_in_parent.company_max_qty
                if not branch_min:
                    branch_min = product_in_parent.branch_min_qty
                if not branch_max:
                    branch_max = product_in_parent.branch_max_qty

            # Set display values
            product.display_company_min_qty = company_min
            product.display_company_max_qty = company_max
            product.display_branch_min_qty = branch_min
            product.display_branch_max_qty = branch_max

    def get_effective_min_max(self):
        """
        Get effective min/max values for the current company.
        Returns dict with company_min, company_max, branch_min, branch_max.
        Inherits from parent company if values are not set.
        """
        self.ensure_one()
        current_company = self.env.company

        # Get values for current company
        result = {
            'company_min': self.company_min_qty,
            'company_max': self.company_max_qty,
            'branch_min': self.branch_min_qty,
            'branch_max': self.branch_max_qty,
        }

        # If current company has a parent and values are not set, inherit from parent
        if current_company.parent_id:
            product_in_parent = self.with_company(current_company.parent_id)

            if not result['company_min']:
                result['company_min'] = product_in_parent.company_min_qty
            if not result['company_max']:
                result['company_max'] = product_in_parent.company_max_qty
            if not result['branch_min']:
                result['branch_min'] = product_in_parent.branch_min_qty
            if not result['branch_max']:
                result['branch_max'] = product_in_parent.branch_max_qty

        return result
