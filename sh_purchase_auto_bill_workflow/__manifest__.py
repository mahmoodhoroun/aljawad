# -*- coding: utf-8 -*-
# Part of Softhealer Technologies

{
    "name": "Purchase Order Automatic Workflow ",

    "author": "Softhealer Technologies",

    "license": "OPL-1",

    "website": "https://www.softhealer.com",

    "support": "support@softhealer.com",

    "version": "0.0.1",

    "category": "Purchases",

    "summary": """Request For Quotation Automatic Workflow Purchase Orders Automatic Workflow
                Purchase Automatic Workflow Purchase Auto Workflow Purchase Order Auto Workflow RFQ
                Auto Workflow Auto Validate Order auto create bill auto validate bill default
                payment method default payment journal Odoo""",

    "description": """This module helps to create an auto workflow in purchase order/request for
                    quotation. The purchase representative can quickly perform all purchase-related
                    operations in one shoot. You can create workflows with automatization and apply
                    it to purchase orders. When you create a request for quotation if you select
                    auto workflow then press the "Confirm" button to proceed with workflow as per
                    the configuration. You can configure auto workflow as per the requirement, fo
                    example, auto validate order, Automatically create & validate bill, default
                    payment journal & default payment method, auto register payments etc.""",

    "depends": [
        "purchase",
        "stock",
        "sh_sale_auto_invoice_workflow"
    ],
    "data": [

        'security/sh_purchase_workflow_groups.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/sh_purchase_auto_workflow_views.xml',
        'views/res_partner_views.xml',
        'views/purchase_order_views.xml',
    ],
    "auto_install": False,
    "installable": True,
    "application": True,
    "images": ["static/description/background.png"],
    "price": "30",
    "currency": "EUR"
}
