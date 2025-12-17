{
    'name': 'Lowest Selling Price',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Add lowest selling price pricelist setting',
    'description': """
        This module adds a new setting field to link with pricelist for lowest selling price.
    """,
    'depends': ['base', 'sale_management', 'sale_discount_total'],
    'data': [
        'security/lowest_price_security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'wizards/confirm_low_price_wizard_view.xml',
        'views/sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
