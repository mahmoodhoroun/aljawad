{
    'name': 'Replenishment Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'High-performance replenishment dashboard with SQL queries',
    'description': """
        Replenishment Dashboard Module
        ===============================
        - High-performance dashboard using SQL queries
        - Real-time stock level monitoring
        - Beautiful JavaScript interface
        - Track sales, purchases, and returns
        - Company and branch filtering
        - Calculate min/max quantities efficiently
    """,
    'author': 'Your Company',
    'depends': ['web', 'stock', 'sale_management', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/replenishment_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'replenishment_dashboard/static/src/css/**/*',
            'replenishment_dashboard/static/src/js/**/*',
            'replenishment_dashboard/static/src/xml/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
