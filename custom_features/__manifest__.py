{
    'name': 'Custom Features',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Custom features for sales and products',
    'description': """
        Custom features including:
        - Price after tax in sale order lines
        - Stock display with warehouse details
        - Configurable warehouse access rights
        - Default customer setting for sales
        - Remove duplicate products functionality
        - Auto-increment serial numbering for product categories
        - Auto-generate product barcodes from category serial
    """,
    'depends': ['base', 'sale_management', 'stock', 'account', 'sh_sale_auto_invoice_workflow', 'commissions_for_customer'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/report_saleorder_document_inherit.xml',
        'views/report_invoice_document_inherit.xml',
        'views/product_template_views.xml',
        'views/product_category_views.xml',
        'views/stock_details_wizard_views.xml',
        'views/res_users_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/res_company_view.xml',
        'views/stock_picking_view.xml',
        'wizerd/stock_picking_return_view.xml',
        'views/account_payment_view.xml',
        'wizerd/account_move_reversal_view.xml',
        'views/account_move_views2.xml',
        'views/purchase_order_report.xml',
        'views/stock_picking_report.xml',
        'views/purchase_order_view.xml',
        'views/account_move_zero_quantities_wizard_views.xml',
        'views/stock_picking_zero_quantities_wizard_views.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'custom_features/static/src/img/img.png',
        ],
        'web.assets_backend': [
            'custom_features/static/src/components/pivot/pivot_style.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
