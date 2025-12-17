# -*- coding: utf-8 -*-
##############################################################################
#
#    Globalteckz
#    Copyright (C) 2013-Today Globalteckz (http://www.globalteckz.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Customer / Supplier statement & customer overdue payment reports',
    'version': '17.00',
    'author': 'Globalteckz',
    'website' : 'https://www.globalteckz.com',
    'category': 'Accounts',
    'summary': 'Apps for print customer statement report print vendor statement payment reminder customer payment followup send customer statement print account statement reports print overdue statement reports send overdue statement print supplier statement reports Customer / Supplier statement & customer overdue payment reports Reports for overdue payments customer over due payments handling suppliers over due payments report customer overdue invoice supplier overdue invoices overdue payments reminder odoo apps',
    'description': """
customer statement
supplier statement
overdue statement
pending statement
customer follow up
customer overdue statement
customer account statement
supplier account statement
Send customer overdue statements by email
send overdue email
outstanding invoice
customer overdue payments
customer statement
invoice
reminder
monthly
    """,
	"price": "49.00",
    "currency": "USD",
    'images': ['static/description/Banner.gif'],
	"live_test_url" : "http://statement12.erpodoo.in:8069",
    "license" : "Other proprietary",
    'depends': ['sale_management',
                'purchase',
                'account',
                'stock',
                'sale_stock',
                ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_statements.xml',
        'report/acc_statemnt_view.xml',
        'report/email_acc_statement.xml',
        'report/email_overdue.xml',
        'report/report_view.xml',
        'views/partner_view.xml',
        'views/send_mail_view.xml',
        'views/account_move_view.xml',
        'views/sale_purchase_view.xml',
        'views/payment_view.xml'
    ],
    'qweb' : [
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
