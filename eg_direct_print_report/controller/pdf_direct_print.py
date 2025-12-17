import json

from odoo.addons.web.controllers.report import ReportController
from odoo import http


class PdfDirectPrint(ReportController):
    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, context=None):
        res = super(PdfDirectPrint, self).report_download(data, context)
        res.headers['Content-Disposition'] = res.headers['Content-Disposition'].replace('attachment', 'inline')
        return res
