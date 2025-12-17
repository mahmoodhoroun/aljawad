# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    group_auto_purchase_workflow = fields.Boolean("Enable Auto Workflow")
    purchase_workflow_id = fields.Many2one('sh.auto.purchase.workflow',
                                           string="Default Workflow")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # is_installed_sale = fields.Boolean(string='Is Sale Module Installed', compute='_compute_is_installed_sale')
    group_auto_purchase_workflow = fields.Boolean("Enable Auto Workflow",
                                                  related="company_id.group_auto_purchase_workflow",
                                                  readonly=False,
                                                  implied_group='sh_purchase_auto_bill_workflow.group_auto_purchase_workflow')
    purchase_workflow_id = fields.Many2one('sh.auto.purchase.workflow',
                                           string="Default Workflow",
                                           related="company_id.purchase_workflow_id",
                                           readonly=False)

    # def _compute_is_installed_sale(self):
    #     for record in self:
    #         record.is_installed_sale = self.env['ir.module.module'].search([('name', '=', 'sale'), ('state', '=', 'installed')], limit=1) and True or False
