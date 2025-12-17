# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
import requests
import json
import re
from .fetch_data import FetchData
from urllib.parse import urlparse, parse_qs
from logging import getLogger
_logger = getLogger(__name__)


class SallaApi:

    def __init__(self, client_id, client_secret, access_token, refresh_token, channel=False, **kw):
        self.channel_id = channel
        self.id = channel.id
        self.env = channel.env
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        # self.pricelist_id = pricelist_id
        # self.location_id = kw.get('location_id')

    def __enter__(self):
        self.import_url = "https://api.salla.dev/admin/v2/"
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        del self

    # def pre_get(self, kw):
    #     options = {}
    #     options['limit'] = kw['page_size']
    #     if 'next_url' in kw:
    #         options['next_url'] = kw['next_url']
    #     return options

    def fetch_data(self, **kw):  # The fetch data object
        return FetchData(self.channel_id, **kw)

    def get_headers(self):
        return {
            'Content-Type': "application/json",
            'Authorization': "Bearer " + str(self.access_token)
        }

    def salla_pagination(self, pagination, kw):
        if pagination.get('links'):
            next_url = pagination.get("links").get('next')
            if next_url:
                kw['next_url'] = next_url
        return kw

    # +++++++++++++++++++Response+++++++++++
    def salla_response(self, endpoint, method="GET", data={}, params={}, headers={}):
        try:
            if not headers:
                headers = self.get_headers()
            if data:
                data = json.dumps(data)
            if not 'query' in endpoint:
                endpoint += '?query=*'
            response = requests.request(
                method, endpoint, headers=headers, data=data, params=params)
            if response.status_code in [200, 201]:
                return response.json()
            try:
                _logger.info('Error: %r', response.json())
            except:
                _logger.info('Error: %r', response)
        except Exception as e:
            _logger.error('Error occurred : %r', e, exc_info=True)
        return []

    # ++++++++++++++++++++++Import++++++++++++++++++++++++++++++++++

    def get_categories(self, **kw):
        endpoint = self.import_url + "categories"
        if kw.get('filter_type') == "id":
            endpoint += f"/{kw.get('object_id')}"
        response = self.salla_response(endpoint)
        if response:
            if response.get('data'):
                if isinstance(response.get('data'), list):  # category by all
                    return self.fetch_data().get_all_categories(response.get('data')), kw
                else:  # category by id
                    # entered id of child category
                    if response.get('data').get('parent_id'):
                        kw.update(
                            {'object_id': response.get('data').get('parent_id')})
                        return self.get_categories(**kw)
                    return self.fetch_data().get_all_categories([response.get('data')]), kw
        return [], kw

    def get_shippings(self, **kw):
        if kw.get('filter_type') == "id":
            endpoint = self.import_url + \
                f"shipping/companies/{kw.get('object_id')}"
        else:
            endpoint = self.import_url+"shipping/companies"
        response = self.salla_response(endpoint)
        if response:
            if response.get('data'):
                if isinstance(response.get('data'), list):
                    return [self.fetch_data().get_shipping_vals(self.channel_id, data) for data in response.get('data')], kw
                else:
                    return [self.fetch_data().get_shipping_vals(self.channel_id, response.get('data'))], kw

        return [], kw

    def get_partners(self, **kw):
        customer_data_list = []
        kw.update({'page_size': 15})  # Customer api has page size of 15
        params = {}
        if kw.get('object_id'):
            endpoint = self.import_url + "customers/" + kw.get('object_id')
        else:
            if kw.get('next_url'):
                endpoint = kw.get('next_url')
            else:
                endpoint = self.import_url + "customers"
                params.update({'page':1})
        response = self.salla_response(endpoint, params=params)
        if response:
            customers = response.get("data", False)
            if isinstance(customers, list):
                for customer in customers:
                    customer_data_list.append(
                        self.fetch_data().process_customer(customer))
                if response.get('pagination'):
                    kw = self.salla_pagination(response.get('pagination'), kw)
                else:
                    kw.update({'page_size': kw.get('page_size')+1})
            else:  # response of customer by id
                customer_data_list.append(
                    self.fetch_data().process_customer(customers))
        return customer_data_list, kw

    # Get products
    def get_products(self, **kw):
        params = {}
        product_data_list = []
        endpoint = self.import_url+f"products"
        if kw.get('filter_type') == "id":
            product_store_ids = list(set(s.strip() for s in kw.get('object_id').split(',')))
            for product_store_id in product_store_ids:
                if product_store_id:
                    endpoint = self.import_url + "products/" + product_store_id
                    response = self.salla_response(endpoint, params=params)
                    if response:
                        product_data = self.fetch_data(**kw).import_product_vals(response.get('data'))
                        # Handle both single product dict and list of product dicts
                        if isinstance(product_data, list):
                            product_data_list.extend(product_data)
                        else:
                            product_data_list.append(product_data)
                        kw.update({'page_size': kw.get('page_size')+1})
        else:
            kw.update({'page_size': kw.get('page_size') if kw.get('page_size') <= 65 else 65})
            if not kw.get('next_url'):
                params = {'page': 1, 'per_page': kw.get('page_size')}
                if (kw.get('salla_product_keyword') and kw.get('salla_enable_keyword')) and (not kw.get('filter_type') == "date"):  # any keyword
                    params.update({'keyword': kw.get('salla_product_keyword')})
            else:
                endpoint = kw.get('next_url')
            response = self.salla_response(endpoint, params=params)
            if response:
                if response.get('data'):
                    if isinstance(response.get('data'), list):
                        for product in response.get('data'):
                            product_data = self.fetch_data(**kw).import_product_vals(product)
                            # Handle both single product dict and list of product dicts
                            if isinstance(product_data, list):
                                product_data_list.extend(product_data)
                            else:
                                product_data_list.append(product_data)
                        if response.get('pagination'):
                            kw = self.salla_pagination(
                                response.get('pagination'), kw)
                        else:
                            kw.update({'page_size': kw.get('page_size')+1})
        return product_data_list, kw

    def get_order_status(self, order_status_id):
        params = {}
        status_list = []
        endpoint = self.import_url + "orders/statuses"
        response = self.salla_response(endpoint, params=params)
        if response.get('data'):
            for data in response.get('data'):
                if str(data.get('original').get('id')) == order_status_id:
                    status_list.append(str(data.get('id')))
                    status_list.append(order_status_id)
        return status_list
        
    # Get Orders
    def get_orders(self, **kw):
        order_data_list = []
        kw.update({'page_size': 15})  # order api has page size or limit is 15
        params = {'expanded': True}  # Getting detailed response per order
        if kw.get('filter_type') == "id":
            order_store_ids = list(set(s.strip() for s in kw.get('object_id').split(',')))
            for order_store_id in order_store_ids:
                if order_store_id:
                    endpoint = self.import_url + "orders/" + order_store_id
                    response = self.salla_response(endpoint, params=params)
                    if response:
                        order_data = self.fetch_data().process_order(response.get('data'))
                        order_data_list.append(order_data)
        else:
            if kw.get('next_url'):
                endpoint = kw.get('next_url')
                if kw.get('salla_order_status'):
                    parsed_url = urlparse(endpoint)
                    query_params = parse_qs(parsed_url.query)
                    page_value = query_params.get('page', [''])[0]
                    if page_value:
                        params.update({'status[]': kw.get('salla_order_status_list_id'), 'page':page_value})
                        endpoint = self.import_url + f"orders"
            else:
                # status = ['566146469','814202285','1473353380','349994915','1723506348','1298199463','525144736']
                # params.update({'status[]': status}) # required to pass status
                if kw.get('filter_type') == "date":
                    params.update({
                        'from_date': kw.get('salla_from_date'),
                        'to_date': kw.get('salla_to_date'),
                    })
                    endpoint = self.import_url + "orders"
                else: # by all
                    if kw.get('salla_order_status'):
                        status_list_id = self.get_order_status(kw.get('salla_order_status')) #### status_list = ['id','original_id','parent_id']
                        params.update({'status[]': status_list_id})
                        kw.update({'salla_order_status_list_id': status_list_id})
                    params.update({'page': 1})
                    endpoint = self.import_url + f"orders"
            response = self.salla_response(endpoint, params=params)
            if response:
                if isinstance(response.get('data'), list):
                    order_data_list = [self.fetch_data().process_order(
                        data) for data in response.get('data')]
                    if response.get("pagination"):
                        kw = self.salla_pagination(response.get('pagination'), kw)
        return order_data_list, kw

    # ++++++++++++++++++++++++Export++++++++++++++++++++++++++++++++++++

    def post_category(self, record, initial_record_id):
        return_list = [False, ""]
        cat_id = self.post_category_data(record, initial_record_id)
        if cat_id:
            return_list = [True, {"id": cat_id}]
        return return_list

    def post_category_data(self, record, initial_record_id):
        p_cat_id = 0
        if record.parent_id:
            parent_id = record.parent_id
            is_parent_mapped = self.channel_id.match_category_mappings(
                odoo_category_id=parent_id.id)
            if not is_parent_mapped:
                p_cat_id = self.post_category(parent_id, initial_record_id)
                if p_cat_id[0]:
                    p_cat_id = p_cat_id[1].get('id')
            else:
                p_cat_id = is_parent_mapped.store_category_id
        return self.export_category_data(record, initial_record_id, p_cat_id)

    def export_category_data(self, record, initial_record_id, parent_cat_id):
        returnid = False
        endpoint = self.import_url + "categories"
        data = {
            'name': record.name,
        }
        if parent_cat_id:
            data.update({'parent_id': parent_cat_id})
        response = self.salla_response(endpoint, method="POST", data=data)
        if response:
            returnid = response.get('data').get("id")
            if record.id != initial_record_id:
                self.channel_id.create_category_mapping(
                    record, returnid, leaf_category=False)
        return returnid

    def image_url(self, record): # Generate Image URL
        config_parameter = self.env['ir.config_parameter']
        url = config_parameter.get_param('web.base.url')
        if not url.endswith('/'):
            url += '/'
        name = record.name.replace(' ', '-').replace('/', '-')
        url += f"channel/image/{record._name}/{record.id}/image_1920/{name}.png"
        return url

    def post_product(self, record):
        options = []
        if record.attribute_line_ids:
            for rec in record.attribute_line_ids:
                data = {
                    "name": rec.attribute_id.name,
                    "display_type": "text",
                }
                values = []
                for val in rec.value_ids:
                    values.append(
                        {"name": val.name, "display_value": val.name})
                data.update({'values': values})
                options.append(data)
        data = self.get_export_product_vals(record, options)
        if data:
            if not record.attribute_line_ids:
                    data.update({"quantity": record.qty_available})
            endpoint = self.import_url + 'products'
            response = self.salla_response(endpoint, method="POST", data=data)
            if response:
                product_id = int(response.get('data').get('id'))
                if response.get('data').get('options') and response.get('data').get('skus'):
                    salla_product_attribute_option_vals = {}
                    for rec in response.get('data').get('skus'):
                        related_options = rec.get("related_option_values")
                        related_options.sort()
                        val = {
                            "_".join(map(str, related_options)): rec.get("id")
                        }
                        salla_product_attribute_option_vals.update(val)
                    variant_ids = self.match_remote_local_variants(self.post_manage_local_variants(
                        record), self.post_manage_remote_variants(response.get('data').get('skus'), response.get('data').get('options')))
                    if variant_ids:
                        record.write(
                            {'salla_product_attribute_options': salla_product_attribute_option_vals or False})
                        return True, {'id': product_id, 'variants': variant_ids}
                if not record.default_code:
                    record.write({'default_code': data.get('sku')})
                return True, {"id": product_id, "variants": [{"id": 'No Variants'}]}
        return False, {}

    def get_export_product_vals(self, record, options):
        sku = record.default_code
        if not len(record.product_variant_ids) > 1:
            if not sku: # Single Variant
                if self.channel_id.sku_sequence_id:
                    sku = self.channel_id.sku_sequence_id.next_by_id()
                else:
                    _logger.info(
                        'Error: SKU(Internal Refrence) or parent code is required for product syncronization')
                    return False
        else: # Multiple Variant 
            sku = record.wk_default_code or '' # Not required to pass SKU
        category_ids = record.channel_category_ids.filtered(
            lambda c: c.instance_id .id == self.channel_id.id).extra_category_ids
        if not category_ids:
            if self.channel_id.default_category_id and self.channel_id._context.get('operation') != 'update':
                category_mapped = self.channel_id.match_category_mappings(
                    odoo_category_id=self.channel_id.default_category_id.id)
                if not category_mapped:  # default category
                    default_category_vals = self.post_category(
                        self.channel_id.default_category_id, self.channel_id.default_category_id.id)
                    store_category_ids = [default_category_vals[1].get(
                        'id')] if default_category_vals[0] else []
                    self.channel_id.create_category_mapping(
                        self.channel_id.default_category_id, store_category_ids[0], leaf_category=False) if store_category_ids else None
                else:
                    store_category_ids = [
                        category_mapped.store_category_id]
            else:
                store_category_ids = []
        else:
            store_category_ids = list(map(lambda x: x.channel_mapping_ids.filtered(
                lambda x: x.channel_id == self.channel_id).store_category_id, category_ids))
        cleaner = re.compile('<.*?>')  # Removing HTML Tags
        subtitle = re.sub(
            cleaner, '', record.description) if record.description else record.name
        return {
            "name": record.name,
            "price": self.channel_id.pricelist_name._get_product_price(record, quantity=1),
            "status": "sale",
            "product_type": "product",
            # "quantity": record.qty_available,
            "description": record.description_sale or "",
            "categories": store_category_ids,
            "sale_price": self.channel_id.pricelist_name._get_product_price(record, quantity=1),
            # "cost_price":self.channel_id.pricelist_name._get_product_price(record, quantity=1),
            "require_shipping": True,
            "maximum_quantity_per_order": 1000,
            "unlimited_quantity": False,
            "sku": sku,
            "hide_quantity": False,
            "enable_upload_image": True,
            "enable_note": True,
            "pinned": True,
            "active_advance": True,
            "subtitle": subtitle,
            "promotion_title": "New",
            "metadata_title": record.name,
            "metadata_description": record.description_sale or "",
            "weight": record.weight,
            "images": [
                {
                    "original": self.image_url(record),
                    "thumbnail": self.image_url(record),
                    "alt": "image",
                    "default": True,
                    "sort": 5
                }
            ],
            'options': options if not self.channel_id._context.get('operation') == "update" else []
        }

    def post_manage_local_variants(self, record):
        """return->eg:
                {product.product(374,): {'Legs': 'Steel', 'Duration': '1 year'}, 
        product.product(375,): {'Legs': 'Steel', 'Duration': '2 year'}, 
        product.product(376,): {'Legs': 'Aluminium', 'Duration': '1 year'}, 
        product.product(377,): {'Legs': 'Aluminium', 'Duration': '2 year'}}
        """
        local_options = {}
        if record.attribute_line_ids:
            for product in record.product_variant_ids:
                values = {}
                for attribute in product.product_template_attribute_value_ids:
                    values.update(
                        {attribute.attribute_id.name: attribute.name})
                local_options.update({product: values})
        return local_options

    def post_manage_remote_variants(self, product_skus, options):
        """return->eg:
                {340856358: {'Legs': 'Steel', 'Duration': '1 year'},
                1715350823: {'Legs': 'Steel', 'Duration': '2 year'}, 
        807095328: {'Legs': 'Aluminium', 'Duration': '1 year'}, 
        232811297: {'Legs': 'Aluminium', 'Duration': '2 year'}}
        """
        options_val = {}
        remote_variants = {}
        for option in options:
            values = {value.get('id'): {option.get('name'): value.get(
                'name')} for value in option.get('values')}
            options_val.update(values)
        for sku in product_skus:
            remote_values = {}
            for value_id in sku.get('related_option_values'):
                remote_values.update(options_val.get(value_id))
            remote_variants.update({sku.get('id'): remote_values})
        return remote_variants

    # Updating variants during export operation
    def match_remote_local_variants(self, local_attributes, remote_attributes):
        """return->eg
                {'product.product(374,)': 340856358}
                {'product.product(375,)': 1715350823}
                {'product.product(376,)': 807095328}
                {'product.product(377,)': 232811297}
        """
        final_dict = {}
        variant_ids = []
        for a, b in local_attributes.items():
            for i, j in remote_attributes.items():
                if b == j:
                    final_dict.update({a: i})
                    break
        for variant_id, remote_id in final_dict.items():  # updating product during export operation
            self.update_product_variants(variant_id, remote_id)
            variant_ids.append({'id': remote_id})
        return variant_ids

    # +++++++++++++++++++++++++++Update+++++++++++++++++++++++++++++

    def update_salla_product(self, record_id, remote_id):
        try:
            if self.channel_id.debug == 'enable':
                _logger.info('Warning: During update opeartion the number of variants can not be updated from odoo to salla')
            number_of_variants = self.channel_id.match_product_mappings(remote_id, limit=False)
            # Check the number of variants
            if not len(number_of_variants) == len(record_id.product_variant_ids):
                _logger.error('Error: Can not change/update the number of variants from odoo to salla for product [{}]'.format(record_id.name))
                return [False, "Error in updating product"]
            endpoint = self.import_url+f'products/{remote_id}'
            data = self.get_export_product_vals(record_id, False)
            if data:
                default_ir_values = self.channel_id.default_multi_channel_values()
                avoid_duplicity = default_ir_values.get('avoid_duplicity')
                if avoid_duplicity:
                    _logger.warning('Warning: Can not update the product sku and barcode, avoid duplicity is enabled')
                    data.pop('sku', False)
                if not record_id.attribute_line_ids:
                    data.update({"quantity": record_id.qty_available})
                response = self.salla_response(
                    endpoint, method="PUT", data=data)
                if response:
                    # manage default code in mappings
                    if not avoid_duplicity:
                        match_template = self.channel_id.match_template_mappings(remote_id)
                        if match_template and data.get('sku', False):
                            match_template.default_code = data.get('sku')
                    if response.get('data').get('skus'):
                        # variable type product
                        for sku in response.get('data').get('skus'):
                            match = self.channel_id.match_product_mappings(
                                remote_id, sku.get('id'))
                            if match and (not avoid_duplicity) and self.channel_id._context.get('operation') == "update":
                                self.update_product_variants(
                                    match.product_name, sku.get('id'), avoid_duplicity)
                    else:
                        # simple type product
                        match = self.channel_id.match_product_mappings(remote_id)
                        if match and (not avoid_duplicity) and self.channel_id._context.get('operation') == "update":
                            match.default_code = record_id.default_code
                    return [True, response]
        except Exception as e:
            _logger.error(
                'Error: exception occurred during update %r', e, exc_info=True)
        return [False, "Error in updating product"]

    def update_product_variants(self, record_id, remote_id, avoid_duplicity = False):
        endpoint = self.import_url + f'products/variants/{remote_id}'
        data = {
            "price": self.channel_id.pricelist_name._get_product_price(record_id, quantity=1),
            "sale_price": self.channel_id.pricelist_name._get_product_price(record_id, quantity=1),
            "stock_quantity": record_id.qty_available,
        }
        if not (self.channel_id._context.get('operation') == "update") or (self.channel_id._context.get('operation') == "update" and (not avoid_duplicity)):
            data.update({
                "sku": record_id.default_code or "",
                "barcode": record_id.barcode or "",
            })
        response = self.salla_response(endpoint, method="PUT", data=data)
        if not response:
            _logger.error('Error in updating product variant %r', remote_id)
                

    def update_category(self, record, initial_record_id, remoteid):
        return_list = [False, '']
        response = self.salla_sync_categories_update(
            record, initial_record_id, remoteid)
        if response:
            return_list = [True, {"id": response}]
        return return_list

    def salla_sync_categories_update(self, record, initial_record_id, remote_id):
        parent_remote_id = False
        if record.parent_id.id:
            is_parent_mapped = self.channel_id.match_category_mappings(
                odoo_category_id=record.parent_id.id)
            if is_parent_mapped:
                parent_remote_id = self.update_category(
                    record.parent_id, initial_record_id, is_parent_mapped.store_category_id)
            else:
                parent_remote_id = self.post_category(
                    record.parent_id, initial_record_id)
            if isinstance(parent_remote_id, list):
                parent_remote_id = parent_remote_id[1].get("id")
        return self.salla_update_category(record, parent_remote_id, remote_id)

    def salla_update_category(self, record, parent_remote_id, remote_id):
        endpoint = self.import_url + f'categories/{remote_id}'
        data = {'name': record.name, }
        if parent_remote_id:
            data.update({'parent_id': parent_remote_id})
        response = self.salla_response(endpoint, method="PUT", data=data)
        if response:
            return response.get('data').get('id')
        return False

    # +++++++++++++++++++++++Core Methods++++++++++++++++++++++++++
    def set_quantity(self, product_id, qty=0, type="product"):
        if type == "product":
            endpoint = "products/quantities/" + product_id
        else:
            endpoint = "products/quantities/variant/" + product_id
        endpoint = self.import_url + endpoint
        data = {
            "quantity": qty,
        }
        res = self.salla_response(endpoint, method="PUT", data=data)
