# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import datetime, timezone
import requests
from urllib.parse import urlencode, urljoin
import random, string
from .sallaAPI import SallaApi

from logging import getLogger
_logger = getLogger(__name__)

auth_url = "https://accounts.salla.sa/oauth2/auth"
token_url = "https://accounts.salla.sa/oauth2/token"


class MultiChannelSale(models.Model):
    _inherit = 'multi.channel.sale'

    salla_client_id = fields.Char(string='Client id')
    salla_client_secret = fields.Char(string='Secret key')
    salla_redirect_url = fields.Char(
        string='Callback-Url', default=lambda self: self.get_redirect_url())
    refresh_token = fields.Char(string='Refresh Toekn')
    access_token = fields.Char(string='Access Toekn')
    salla_token_expiry = fields.Datetime()
    salla_verification_key = fields.Char(string="Verification Key", copy=False, default=lambda self: self.get_verification_key())

    def get_verification_key(self): # Generate 16 characters random string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    def get_redirect_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return  urljoin(base_url, 'salla/authenticate')
    
    def salla_available_configs(self):
        return [
                # Webhooks Add from extension when implemented
                # 'webhook_available', 
                # 'create_order_webhook',
                # 'update_order_webhook',

                # base
                # 'child_store_config', # Child for existing channel

                # Import Crons
                'cron_available',
                'import_order_cron',
                'order_created_after',
                # 'order_updated_after',
                # 'import_product_cron',
                # 'product_created_after',
                # 'product_updated_after',
                # 'import_partner_cron',
                # 'partner_created_after',
                # 'partner_updated_after',
                'import_category_cron',

                # realtime export
                'sync_order_invoice',
                'sync_order_shipment',
                'sync_order_cancel',
            ]
        
    @api.constrains('salla_verification_key')
    def validate_vefication_key(self):
        key = self.salla_verification_key
        if len(key) < 8:
            raise UserError('The verification key should be minimum 8 characters long')
        channel = self.search([('channel','=','salla'),('salla_verification_key','=',key)])
        if len(channel) > 1:
            channel = channel - self
            raise UserError(f'The verification key [ {key} ] is already exists in other channel [ID: {channel.id}]')


    def write(self, vals):
        for record in self:
            if record.channel == "salla" and (vals.get('salla_client_id') or vals.get('salla_client_secret')):
                vals.update({'refresh_token': False})
                # self.write({'refresh_token': False})
        return super(MultiChannelSale, self).write(vals)

    def get_core_feature_compatible_channels(self):
        channels = super(MultiChannelSale,
                         self).get_core_feature_compatible_channels()
        channels.append('salla')
        return channels

    def get_channel(self):
        channels = super(MultiChannelSale, self).get_channel()
        channels.append(('salla', 'Salla'))
        return channels

    @api.model
    def get_info_urls(self):
        urls = super(MultiChannelSale,self).get_info_urls()
        urls.update(
            salla = {
                'blog' : 'https://webkul.com/blog/user-guide-for-salla-odoo-connector/',
                'store': 'https://store.webkul.com/salla-odoo-connector.html',
            },
        )
        return urls

    def get_sallaApi(self, **kw):
        with SallaApi(self.salla_client_id, self.salla_client_secret, self.access_token, self.refresh_token, channel=self, **kw) as api:
            return api

    def connect_to_salla(self):
        scope = '''offline_access products.read_write'''
        data = {
            'client_id': self.salla_client_id,
            'scope': scope,
            'response_type': 'code',
            # 'approval_prompt':'auto',
            'state': self.salla_verification_key
        }
        url = '?'.join([auth_url, urlencode(data)])
        response = requests.post(url)
        if response.status_code in [200, 201]:
            return {
                'type': 'ir.actions.act_url',
                'target': 'self',
                'url': url
            }
        else:
            return self.display_message("<span class='text-danger'>Authentication failed, Please verify the added Client Keys and Redirect URI</p>")
            

    def create_salla_connection(self, kwargs):
        code = kwargs['code']
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = urlencode({
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.salla_client_id,
            'client_secret': self.salla_client_secret,
        })
        response = requests.post(token_url, data, headers=headers)
        if response.status_code in [200, 201]:
            res = response.json()
            refresh_token = res.get('refresh_token', '')
            access_token = res.get('access_token', '')
            return self.write({
                'state': 'validate',
                'refresh_token': refresh_token,
                'access_token': access_token,
                'salla_token_expiry': datetime.now(),
            })
        else:
            _logger.error(
                'Authentication failed, please verify the added keys in the channel')
            _logger.info(response.content)
        return False

    def get_user_info(self):  # Call the api to check the tokens: valid or not
        api = self.get_sallaApi()
        endpoint = "https://api.salla.dev/admin/v2/oauth2/user/info"
        res = api.salla_response(endpoint)
        if res:
            return True
        return False

    def connect_salla(self):
        return self.getAccessToken()

    def getAccessToken(self):
        status = True
        if not self.refresh_token:  # Connection first time
            status = False
            return status, "<p class='text-warning'>No Connection exists with salla, please create connection first</p>"
        if self._context.get('operation') and self.salla_token_expiry:
            diff = datetime.now() - self.salla_token_expiry
            token_time = float(diff.total_seconds()/(60*60))
            if token_time < 7:  # condition for 7 days, Token expires in 14 days
                return status, 'Token is not expired yet'
        message = "<p class='text-danger'>Error: something went wrong in getting tokens</p>"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Bearer ' + self.access_token,
        }
        data = urlencode({
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.salla_client_id,
            'client_secret': self.salla_client_secret,
        })
        response = requests.post(token_url, data=data, headers=headers)
        if response.status_code in [200, 201]:
            res = response.json()
            message = "<p class='text-success'>Connection refreshed successfully with Salla</p>"
            self.write({
                'state': 'validate',
                'refresh_token': res.get('refresh_token', ''),
                'access_token': res.get('access_token', ''),
                'salla_token_expiry': datetime.now(),
            })
        else:
            status = False
            if not self._context.get('operation'):
                self.state = "error"
            _logger.error(response.content)
            message += '<br/>'+ str(response.content)
        return status, message

    def import_salla(self, object, **kw): # if refresh token expired, channel state will be error
        self.with_context(operation=True).getAccessToken()
        with SallaApi(self.salla_client_id, self.salla_client_secret, self.access_token, self.refresh_token, channel=self, **kw) as api:
            if object == 'res.partner':
                data_list, kw = api.get_partners(**kw)
            elif object == 'sale.order':
                data_list, kw = api.get_orders(**kw)
            elif object == "product.template":
                data_list, kw = api.get_products(**kw)
            elif object == "product.category":
                data_list, kw = api.get_categories(**kw)
                kw.update({'page_size': float('inf')})  # no limit for category
            elif object == "delivery.carrier":
                data_list, kw = api.get_shippings(**kw)
            else:
                data_list = []
                kw = {'message': 'Selected Channel does not allow this.'}
            if object in ['res.partner', 'product.template', 'sale.order']:
                kw.update({'page_size': kw.get('page_size') +
                           1 if not kw.get('next_url') else kw.get('page_size')})
            if object in ['sale.order']:
                if data_list and (kw.get('from_cron') and not kw.get('import_order_date_updated')):
                    self.import_order_date = datetime.strptime(
                        data_list[0].get('date_order'), "%Y-%m-%d %H:%M:%S.%f")
                    kw.update({'import_order_date_updated': True})
            return data_list, kw

    def export_salla(self, record, **kw): # if token expired, channel will be in error
        self.with_context(operation=True).getAccessToken()
        with SallaApi(self.salla_client_id, self.salla_client_secret, self.access_token, self.refresh_token, channel=self, **kw) as api:
            if record._name == 'product.category':
                return api.post_category(record, record.id)
            elif record._name == 'product.template':
                res, object = api.post_product(record)
                return res, object
            else:
                raise NotImplementedError

    def update_salla(self, record, get_remote_id):
        try:
            self.with_context(operation=True).getAccessToken()
            channel = self.with_context(operation='update')
            with SallaApi(self.salla_client_id, self.salla_client_secret, self.access_token, self.refresh_token, channel=channel) as api:
                data_list = [False, {}]
                remote_id = get_remote_id(record)
                if record._name == 'product.template':
                    data_list = api.update_salla_product(record, remote_id)
                elif record._name == "product.category":
                    data_list = api.update_category(
                        record, record.id, remote_id)
        except Exception as e:
            _logger.error('Error: occurred %r', e, exc_info=True)
        return data_list

    def sync_quantity_salla(self, mapping, qty):
        with SallaApi(self.salla_client_id, self.salla_client_secret, self.access_token, self.refresh_token, channel=self) as api:
            if mapping.store_product_id == mapping.store_variant_id or mapping.store_variant_id == "No Variants":
                typ = "product"
                product_id = mapping.store_product_id
            else:
                typ = "variant"
                product_id = mapping.store_variant_id
            return api.set_quantity(product_id, qty, typ)

    # ++++++++++++++++++++++CORE METHODS++++++++++++++++++++++++
    def salla_post_do_transfer(self, stock_picking, mapping_ids, result):
        self.update_salla_order_status('delivered', mapping_ids.store_order_id)

    def salla_post_confirm_paid(self, invoice, mapping_ids, result):
        self.update_salla_order_status('completed', mapping_ids.store_order_id)

    def salla_post_cancel_order(self, sale_order, mapping_ids, result):
        self.update_salla_order_status('canceled', mapping_ids.store_order_id)

    def update_salla_order_status(self, slug, remote_id):
        "under_review, payment_pending , canceled , delivered, completed , shipped , restored , in_progress, delivering, restoring"
        try:
            order_status = self.order_state_ids.filtered(
                lambda order_state_id: order_state_id.channel_state == slug
            )
            if order_status:
                api = self.get_sallaApi()
                endpoint = api.import_url + f"orders/{remote_id}/status"
                data = {'slug': slug}
                if slug == 'completed' and order_status[0].odoo_set_invoice_state != 'paid':
                    _logger.error(
                        'Error: set invoice state in order state mapping for \'completed\' channel order state should be paid in channel configuration')
                else:
                    response = api.salla_response(
                        endpoint, method="POST", data=data)
            else:
                _logger.warning(
                    'Error: Can not update order state, please create order state  mapping for [{}] status in channel configuration'.format(slug))
        except Exception as e:
            _logger.error(
                'Exception occurred during realtime status sync to: {}'.format(slug), exc_info=True)


# ==================== Import Crons ==============================

    def salla_import_order_cron(self):  # Cron implemented
        _logger.info("+++++++++++Import Order Cron Started++++++++++++")
        kw = dict(
            object="sale.order",
            salla_from_date=self.import_order_date,
            salla_to_date=datetime.now(timezone.utc),
            from_cron=True
        )
        if self.import_order_date:
            kw.update({'filter_type': 'date'})
        self.env["import.operation"].create({
            "channel_id": self.id,
        }).import_with_filter(**kw)

    def salla_import_category_cron(self):  # Cron implemented
        _logger.info("+++++++++++Import Category Cron Started++++++++++++")
        kw = dict(
            object="product.category",
            from_cron=True,
        )
        self.env["import.operation"].create({
            "channel_id": self.id,
        }).import_with_filter(**kw)

    def salla_import_product_cron(self):
        _logger.info(
            "+++++ Import Product Cron is not supported in Salla Connector ++++++")

    def salla_import_partner_cron(self):
        _logger.info(
            "+++++ Import Partner Cron is not supported in Salla Connector ++++++")
