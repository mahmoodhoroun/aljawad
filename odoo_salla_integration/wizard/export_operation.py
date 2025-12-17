# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import models

# Export category
class ExportCategory(models.TransientModel):
    _inherit = "export.categories"

    def export_salla_categories(self):
        return self.env['export.operation'].create(
            {
                'channel_id': self.channel_id.id,
                'operation': self.operation,
            }
        ).export_button()

# Export template
class ExportCategory(models.TransientModel):
    _inherit = "export.templates"

    def export_salla_templates(self):
        return self.env['export.operation'].create(
            {
                'channel_id': self.channel_id.id,
                'operation': self.operation,
            }
        ).export_button()