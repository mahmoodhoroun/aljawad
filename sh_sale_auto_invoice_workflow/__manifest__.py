# -*- coding: utf-8 -*-
# Part of Softhealer Technologies

{
    "name": "Sale Order Automatic Workflow ",

    "author": "Softhealer Technologies",

    "license": "OPL-1",

    "website": "https://www.softhealer.com",

    "support": "support@softhealer.com",

    "version": "0.0.2",

    "category": "Sales",

    "summary": """Quotation Automatic Workflow Sales Order Automatic Workflow for Sales Automatic
                Workflow Sale Order Auto Workflow Quotation Auto Workflow Auto delivery order auto
                create invoice auto validate invoice default payment website auto workflow sale
                auto workflow auto payment Auto Sales Workflow Auto Sale Workflow Automatic
                Workflow Of Sale Order Automatic Sale Order Workflow Odoo""",

    "description": """This module helps to create an auto workflow in sale order/quotation.
                    A salesperson can quickly perform all sales-related operations in one shoot.
                    You can create workflows with automatization and apply it to sales orders.
                    When you create a quotation if you select auto workflow then press the
                    "Confirm" button to proceed with workflow as per the configuration. You can
                    configure auto workflow as per the requirement, for example, Automatically
                    create the delivery order, auto-create & validate invoice, default payment
                    journal & default payment method, auto register payments, auto invoice send
                    by email, etc.""",
    "depends": ["sale_management", "stock"],
    "data": [

        'security/sh_sale_workflow_groups.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/sh_auto_sale_workflow_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_view.xml',
        'wizard/confirm_transfer_wizard_view.xml',

    ],
    "auto_install": False,
    "installable": True,
    "application": True,
    "images": ["static/description/background.png"],
    "price": "30",
    "currency": "EUR"
}
