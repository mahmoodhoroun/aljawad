from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    sales_workflow_id = fields.Many2one('sh.auto.sale.workflow', string='Sales Workflow')
    type = fields.Selection([
        ('cash', 'Cash'),
        ('credit', 'Credit'),
    ], string="Type")

    def update_sales_workflow(self):
        for record in self:
            sale_order = self.env['sale.order'].search([('invoice_ids', 'in', record.ids)], limit=1)
            if sale_order:
                record.sales_workflow_id = sale_order.workflow_id
                record.type = sale_order.workflow_id.type