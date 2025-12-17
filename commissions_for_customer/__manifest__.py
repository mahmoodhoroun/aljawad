{
    'name': 'Sales Commissions',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Manage sales commissions',
    'description': """
        This module allows you to manage sales commissions for salespeople.
        Features:
        - Track commission numbers
        - Link commissions to quotations and invoices
        - Calculate commission values based on rates
        - Monitor payment status
    """,
    'depends': ['base', 'sale_management', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'wizards/commission_payment_wizard_views.xml',
        'views/commission_views.xml',
        # 'views/res_users_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_move_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'commissions_for_customer/static/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
