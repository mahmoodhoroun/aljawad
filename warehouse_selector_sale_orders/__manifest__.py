{
    'name': 'Sale Lines Multi Warehouse',
    'version': '15.0',
    "category": 'warehouses',
    'author': 'CustomizeApps',
    'summary': "sale lines multi warehouse app select multiple warehouses sales order line deliver goods different locations default warehouse automatic quantity selection inventory management stockouts automated delivery orders",
    'description': """ 
=======================================
Sale Lines Multi Warehouse
=======================================

Enhance your sales order management with the **Sale Lines Multi Warehouse** app. This app allows you to select multiple warehouses for each sale order line, enabling you to deliver goods from different locations for the same product. If no warehouse is selected, the system will automatically use the default warehouse.

Key Features
============

Multiple Warehouse Selection
----------------------------
- Choose multiple warehouses for each sale order line.
- Ensure products can be sourced from various locations to meet customer demands.

Automatic Warehouse Quantity Selection
--------------------------------------
- If the main warehouse lacks sufficient stock, the system will automatically allocate the remaining quantity from other warehouses within the same company.
- Streamline your inventory management and reduce the risk of stockouts.

Automated Delivery Orders
-------------------------
- When multiple warehouses are selected, either manually or automatically, Odoo will create separate delivery orders for each warehouse.
- Simplify the logistics of fulfilling orders from multiple locations.

Benefits
========

Improved Order Fulfillment
--------------------------
Meet customer demands more efficiently by utilizing stock from various warehouses.

Optimized Inventory Management
------------------------------
Automatically balance stock across multiple locations without manual intervention.

Enhanced Operational Efficiency
-------------------------------
Reduce delays and errors in order processing with automated delivery order creation.

With **Sale Lines Multi Warehouse**, manage your sales orders with greater flexibility and ensure timely delivery to your customers by leveraging the full potential of your warehouse network.
                   """,
    "depends": ['sale_stock', 'sale_management', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/sale_view.xml',
        'views/res_config_settings_views.xml',
        # 'views/hide_company_switch.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'warehouse_selector_sale_orders/static/src/js/switch_company_menu.js',
            'warehouse_selector_sale_orders/static/src/xml/switch_company_menu.xml',
        ],
    },

    "images": ['static/description/warehouse_selector_sale_orders_banner.png'],
    'price': 19.0,
    'application': True,
    'installable': True,
    'currency': 'USD',
    'license': 'OPL-1',
}
