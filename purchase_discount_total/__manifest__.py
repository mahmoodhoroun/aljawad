{
    'name': 'Purchase Discount on Total Amount',
    'version': '18.0.1.1.0',
    'category': 'Purchase Management',
    'author': 'Mahmood Haroun',
    'maintainer': 'Mahmood Haroun',
    'depends': ['purchase', 'account',],
    'data': [
        'views/purchase_order_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
