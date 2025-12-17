# -*- coding: utf-8 -*-

from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    ks_move_id = fields.Many2one('multicompany.transfer.stock.line', 'Stock Move Id')


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    ks_custom_line = fields.Boolean(string='Custom Line')
