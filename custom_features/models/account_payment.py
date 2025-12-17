from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_preview_payment(self):
        self.ensure_one()
        report = self.env.ref('custom_invoice.action_report_custom_payment')
        action = report.report_action(self)
        action['id'] = report.id
        return action
        