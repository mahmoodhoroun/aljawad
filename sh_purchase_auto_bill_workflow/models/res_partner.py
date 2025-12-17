# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    purchase_workflow_id = fields.Many2one(
        'sh.auto.purchase.workflow', string="Purchase Workflow")
