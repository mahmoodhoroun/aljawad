{
    'name': 'Remove Odoo Brand',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Remove Odoo branding from the interface',
    'description': '''
        This module removes Odoo branding elements from the user interface:
        - Removes Documentation link
        - Removes Support link
        - Removes Odoo Account link
        - Replaces default favicon
    ''',
    'depends': ['web'],
    'data': [
        'views/webclient_templates.xml',
        'views/auth_signup_templates_email.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'remove_odoo_brand/static/src/js/user_menu_items.js',
            'remove_odoo_brand/static/src/js/sale_action_helper/sale_action_helper.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
