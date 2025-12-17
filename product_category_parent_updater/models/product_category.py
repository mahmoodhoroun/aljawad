from odoo import models, api, _
from odoo.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    def action_update_from_parent(self):
        """Update category fields from parent category"""
        for category in self:
            if not category.parent_id:
                continue
                
            parent = category.parent_id
            
            # Fields to update from parent
            fields_to_update = {
                'property_cost_method': parent.property_cost_method,
                'property_valuation': parent.property_valuation,
                'property_account_creditor_price_difference_categ': parent.property_account_creditor_price_difference_categ.id if parent.property_account_creditor_price_difference_categ else False,
                'property_account_income_categ_id': parent.property_account_income_categ_id.id if parent.property_account_income_categ_id else False,
                'property_account_expense_categ_id': parent.property_account_expense_categ_id.id if parent.property_account_expense_categ_id else False,
                'property_stock_valuation_account_id': parent.property_stock_valuation_account_id.id if parent.property_stock_valuation_account_id else False,
                'property_stock_journal': parent.property_stock_journal.id if parent.property_stock_journal else False,
                'property_stock_account_input_categ_id': parent.property_stock_account_input_categ_id.id if parent.property_stock_account_input_categ_id else False,
                'property_stock_account_output_categ_id': parent.property_stock_account_output_categ_id.id if parent.property_stock_account_output_categ_id else False,
                'property_stock_transfer_account_categ_id' : parent.property_stock_transfer_account_categ_id.id if parent.property_stock_transfer_account_categ_id else False,
            }
            
            # Update the category with parent values
            category.write(fields_to_update)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Category fields updated from parent successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_update_all_from_parent(self):
        """Update all selected categories from their respective parents"""
        categories_updated = 0
        categories_without_parent = 0
        
        for category in self:
            if category.parent_id:
                category.action_update_from_parent()
                categories_updated += 1
            else:
                categories_without_parent += 1
        
        message = _('Updated %d categories from their parents.') % categories_updated
        if categories_without_parent > 0:
            message += _(' %d categories skipped (no parent).') % categories_without_parent
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Update Complete'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }
