{
    'name': 'Product BoM Components',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Manage Bill of Materials components directly from product form with bidirectional sync',
    'description': """
        Product BoM Components
        ======================

        This module adds a new page in the product form to manage Bill of Materials components
        with automatic bidirectional synchronization.

        Features:
        ---------
        * View and edit BoM components directly from product form
        * Automatic bidirectional sync between product and BoM
        * Changes in product form update the BoM automatically
        * Changes in BoM update the product form automatically
        * Load existing BoM components with one click
        * Drag and drop to reorder components
        * Auto-fill Unit of Measure from product

        Requirements:
        ------------
        * MRP module (optional - gracefully handles when not installed)
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
