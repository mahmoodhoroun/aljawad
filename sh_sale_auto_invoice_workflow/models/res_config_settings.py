from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    group_auto_sale_workflow = fields.Boolean("Enable Auto Workflow")
    workflow_id = fields.Many2one('sh.auto.sale.workflow',
                                  string="Default Workflow")

    # default_customer_id = fields.Many2one('res.partner',
    #                                      string="Default Customer")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_auto_sale_workflow = fields.Boolean("Enable Auto Workflow",
                                              related="company_id.group_auto_sale_workflow",
                                              readonly=False,
                                              implied_group='sh_sale_auto_invoice_workflow.group_auto_sale_workflow')
    workflow_id = fields.Many2one('sh.auto.sale.workflow',
                                  string="Default Workflow",
                                  related="company_id.workflow_id",
                                  readonly=False)
    
    # default_customer_id = fields.Many2one('res.partner',
    #                                      string="Default Customer",
    #                                      related="company_id.default_customer_id",
    #                                      readonly=False)
