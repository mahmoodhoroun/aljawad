# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMoveReversalInherit(models.TransientModel):
    _inherit = 'account.move.reversal'

    type = fields.Selection([
        ('cash', 'Cash'),
        ('credit', 'Credit')
    ], string='Type', required=True, default='cash')

    def _prepare_default_reversal(self, move):
        # Inherit the original method to add our custom field
        vals = super(AccountMoveReversalInherit, self)._prepare_default_reversal(move)
        # Add the type to the reversal values
        vals.update({
            'type': self.type,
        })
        return vals
