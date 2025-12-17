# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
    'name':  'Salla Odoo Connector | Odoo Multichannel',
    'summary':              """
                            Odoo Salla Connectors integrates your Odoo with salla to make 
                            the shopping experience seamless. The module allows you to 
                            sync products, categories, and sync orders to Odoo so that 
                            you can efficiently manage.
                            Multichannel is also compatible with these webkul apps
                            Amazon Connector Ebay Connector Magento Connector Woocommerce
                            Connector Shopify Connector Shopware Connector Walmart Wix Connector
                            Connector Prestashop Connector flipkart connector odoo Apps
                            Ecommerce Connectors for salla multi-channel salla webkul connectors
                            """,
    'description':          """
                                Salla Connector for Multichannel
                                Integrate Salla E-Commerce with Odoo.
                                Odoo Salla Connector integrates your Odoo with Salla to make the shopping experience seamless. 
                                The module allows you to sync products, categories, and orders to Odoo so that you can efficiently manage. 
                            """,
    'category': 'eCommerce',
    'version': '1.1.4',
    'sequence': 1,
    'author': 'Webkul Software Pvt. Ltd.',
    'maintainer': 'Webkul Software Pvt. Ltd.',
    'license': 'Other proprietary',
    'website': 'https://store.webkul.com/salla-odoo-connector.html',
    'live_test_url': 'https://odoodemo.webkul.com?module=odoo_salla_integration',
    'depends': ['odoo_multi_channel_sale'],
    'data': [
        'data/data.xml',
        'views/multi_channel_sale.xml',
        'wizard/import_operation.xml',
        'wizard/export_operation.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_salla_integration/static/src/xml/instance_dashboard.xml',
        ],
    },
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
    'price': 199,
    'currency': 'USD',
    'pre_init_hook': 'pre_init_check',
}
