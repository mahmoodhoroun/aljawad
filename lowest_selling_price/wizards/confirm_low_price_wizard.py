from odoo import models, fields, api, _

class ConfirmLowPriceWizard(models.TransientModel):
    _name = 'confirm.low.price.wizard'
    _description = 'Confirm Low Price Wizard'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    text = fields.Text(string='Text')
    
    def action_confirm(self):
        self.ensure_one()
        return self.sale_order_id.action_confirm()
