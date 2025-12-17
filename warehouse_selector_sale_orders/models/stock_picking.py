from odoo import models, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        
        
        # Get all related pickings from the same sale order
        for picking in pickings:
            if picking.sale_id and picking.sale_id.workflow:
                workflow = picking.sale_id.workflow
                
                # Get all pickings from this sale order
                all_pickings = picking.sale_id.picking_ids
                
                # Check if workflow is configured to validate order and force transfer
                # if workflow.validate_order and workflow.force_transfer:
                for pick in all_pickings:
                    try:
                        # Get the original user's company
                        original_company = self.env.company

                        # Switch to the picking's company temporarily
                        self.env.user.company_id = pick.company_id
                        self.env.company = pick.company_id
                        
                        pick = pick.with_company(pick.company_id)
                        
                        # First confirm the picking if it's in draft state
                        if pick.state == 'draft':
                            pick.action_confirm()
                        
                        # Force availability for all moves
                        if pick.state in ['confirmed', 'waiting']:
                            for move in pick.move_ids:
                                move.quantity_done = move.product_uom_qty
                            pick.with_context(skip_backorder=True, force_period_date=pick.scheduled_date).action_assign()
                        
                        # Handle immediate transfer case
                        if pick.picking_type_id.auto_show_reception_report:
                            pick.immediate_transfer = True
                            for move in pick.move_ids:
                                move.quantity = move.product_uom_qty
                            for move_line in pick.move_line_ids:
                                move_line.quantity = move_line.product_uom_qty
                        
                        # Set quantities for all moves
                        for move in pick.move_ids:
                            move.quantity_done = move.product_uom_qty
                        
                        # Validate the picking if not already done
                        if pick.state not in ['done', 'cancel']:
                            pick.with_context(skip_backorder=True).button_validate()
                            
                    except Exception as e:
                        # Log error but don't stop the process
                        pick.message_post(body=_(
                            "Failed to auto-validate picking: %s", str(e)
                        ))
                    finally:
                        # Always restore the original company
                        self.env.user.company_id = original_company
                        self.env.company = original_company
        
        return pickings
