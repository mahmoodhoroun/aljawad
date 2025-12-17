{
    "name": "Auto Reconcile Payment Multi Invoice For Customer and Vendor || Multiple Invoice Payment  ",
    "version": "1.2",
    "description": """
        Using this module you can pay multiple invoice payment in one click.
    """,
    "author" : "Sonod ERP",
    'sequence': 1,
    "email": 'info@sonod.tech',
    "website":'',
    'category':"Accounting",
    'summary':"",
    'license': 'LGPL-3',
    "depends": [
        "account",
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/actions_view.xml',
        'views/menuitem_view.xml',
        'views/multiinvoice_payment_view.xml',

        'report/account_payment_report.xml',
        # 'report/report_custom_payment.xml',
    ],
    'assets': {
        "web.assets_qweb": [
            "/auto_reconcile_payment/static/src/css/style.css"
        ],
        'web.report_assets_pdf': [
            "/auto_reconcile_payment/static/src/css/style.css"
        ],
        'web.report_assets_common': [
            'auto_reconcile_payment/static/src/css/style.css',
        ]
    },
    'qweb': [],
    "images": [],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}

