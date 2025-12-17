from odoo import models, fields, api
from odoo.exceptions import UserError

class CommissionPaymentWizard(models.TransientModel):
    _name = 'commission.payment.wizard'
    _description = 'Commission Payment Wizard'

    commission_ids = fields.Many2many('sales.commission', string='Commissions')
    payment_date = fields.Date(string='Payment Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Amount', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal',
        domain=[('type', 'in', ['bank', 'cash'])], required=True)
    communication = fields.Char(string='Memo', compute='_compute_communication', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', 
        default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company', 
        default=lambda self: self.env.company)

    @api.depends('commission_ids')
    def _compute_communication(self):
        for wizard in self:
            commission_numbers = wizard.commission_ids.mapped('commission_number')
            wizard.communication = 'Payment for commission(s): ' + ', '.join(commission_numbers)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'commission_ids' in fields_list:
            active_ids = self.env.context.get('active_ids', [])
            commissions = self.env['sales.commission'].browse(active_ids)
            total_commission = sum(commissions.mapped('commission_value'))
            res.update({
                'commission_ids': [(6, 0, active_ids)],
                'amount': total_commission,
            })
        return res

    def action_create_payments(self):
        self.ensure_one()
        if not self.commission_ids:
            raise UserError('No commissions selected.')
        
        for record in self.commission_ids:
            if record.status != 'confirmed':
                raise UserError('All selected commissions must be confirmed before payment.')

        company = self.env.company
        if not company.commission_payable_account_id:
            raise UserError('Please configure commission payable account in settings first!')

        # Create journal entry
        move_vals = {
            'ref': self.communication,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'move_type': 'entry',
            'line_ids': [
                # Credit line - Commission Payable account
                (0, 0, {
                    'name': 'Payment for commission',
                    'debit': 0.0,
                    'credit': self.amount,
                    'account_id': self.journal_id.default_account_id.id,
                    'partner_id': self.commission_ids[0].customer_salesperson.id,
                }),
                # Debit line - Bank/Cash account
                (0, 0, {
                    'name': 'Payment for commission',
                    'debit': self.amount,
                    'credit': 0.0,
                    'account_id': company.commission_payable_account_id.id,
                    'partner_id': self.commission_ids[0].customer_salesperson.id,
                })
            ]
        }

        move = self.env['account.move'].create(move_vals)
        move.commission_id = self.commission_ids[0].id
        move.action_post()

        # Update commissions
        self.commission_ids.write({
            'status': 'paid',
            'move_id': move.id,
        })

        return {
            'name': 'Journal Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current'
        }
