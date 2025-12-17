{
    'name': 'Product Category Parent Updater',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Update product category fields from parent category',
    'description': """
        This module adds a button to the product category list view that allows
        updating specific fields from the parent category to child categories.
        
        Updated fields:
        - property_valuation
        - property_account_creditor_price_difference_categ
        - property_account_income_categ_id
        - property_account_expense_categ_id
        - property_stock_valuation_account_id
        - property_stock_journal
        - property_stock_account_input_categ_id
        - property_stock_account_output_categ_id
    """,
    'author': 'Custom Development',
    'depends': ['product', 'stock_account'],
    'data': [
        'views/product_category_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
