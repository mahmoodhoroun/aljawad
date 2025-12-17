# -*- coding: utf-8 -*-
# Copyright 2025 Sveltware Solutions

{
    'name': 'Custom Invoice',
    'category': 'Custom Invoice',
    'summary': 'Custom Invoice',
    'version': '1.0',
    'license': 'OPL-1',
    'author': 'Mahmood Haroun',
    'support': 'mahmood.a.haroun@gmail.com',
    'sequence': 777,
    'depends': ['base', 'account', 'sale', 'custom_features'],
    'data': [
        'views/arabic_layout.xml',
        'views/report_custom_invoice_template.xml',
        'views/report_custom_sales_template.xml',
        'views/report_custom_payment.xml',
        'views/custom_report.xml',
        'views/account_move_views.xml',
        # 'views/sale_order_view.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            '/custom_invoice/static/src/fonts/Tajawal/Tajawal-Regular.ttf',
            '/custom_invoice/static/src/css/arabic_fonts.css',
            '/custom_invoice/static/src/scss/arabic_report.scss',
        ],
    },
    'installable': True,
    'application': True,
}
