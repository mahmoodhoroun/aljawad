# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class AutoPurchaseWorkflow(models.Model):
    _name = 'sh.auto.purchase.workflow'
    _description = "Auto Purchase Workflow"

    name = fields.Char(string="Name", required=True)
    validate_order = fields.Boolean(string="Validate Order")
    create_bill = fields.Boolean(string="Create Bill")
    validate_bill = fields.Boolean(string="Validate Bill")
    register_payment = fields.Boolean(string="Register Payment")
    purchase_journal = fields.Many2one(
        'account.journal', string="Purchase Journal",)
    payment_journal = fields.Many2one(
        'account.journal', string="Payment Journal",)
    payment_method = fields.Many2one(
        'account.payment.method', string="Payment Method")
    allow_multiple_payment = fields.Boolean(string="Allow Multiple Payment")
    user_ids = fields.Many2many('res.users', string='Authorized Users', 
                            help="Users authorized to use this workflow. If empty, all users can use it.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)