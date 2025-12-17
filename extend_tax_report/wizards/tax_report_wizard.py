# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountingTaxReport(models.TransientModel):
    _inherit = 'kit.account.tax.report'

    tax_ids = fields.Many2many('account.tax', string="Taxes")

    def _print_report(self, data):
        if self.tax_ids:
            data['form']['tax_ids'] = self.tax_ids.ids
        else:
            data['form']['tax_ids'] = self.env['account.tax'].search([]).ids

        if self._context.get('excel_report'):
            return self.env.ref('extend_tax_report.action_report_account_tax_excel').report_action(
                self, data=data)
        else:
            return super(AccountingTaxReport, self)._print_report(data)

