from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    commission_account_id = fields.Many2one(
        'account.account',
        string='Commission Account'
    )
    commission_payable_account_id = fields.Many2one(
        'account.account',
        string='Commission Payable Account'
    )
    commission_journal_id = fields.Many2one(
        'account.journal',
        string='Commission Journal'
    )
    auto_confirm = fields.Boolean(
        string='Auto Confirm', help='When you check this field, the commission will be automatically confirmed when created'
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    commission_account_id = fields.Many2one(
        'account.account',
        string='Commission Account',
        related='company_id.commission_account_id',
        readonly=False
    )
    commission_payable_account_id = fields.Many2one(
        'account.account',
        string='Commission Payable Account',
        related='company_id.commission_payable_account_id',
        readonly=False
    )
    commission_journal_id = fields.Many2one(
        'account.journal',
        string='Commission Journal',
        related='company_id.commission_journal_id',
        readonly=False
    )
    auto_confirm = fields.Boolean(
        string='Auto Confirm',
        related='company_id.auto_confirm',
        readonly=False
    )
        