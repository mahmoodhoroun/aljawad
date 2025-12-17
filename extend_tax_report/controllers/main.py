# -*- coding: utf-8 -*-
from odoo.http import content_disposition, route, request, Controller
from odoo.tools.safe_eval import safe_eval
import json
import time


class CustomXlsxReportController(Controller):

    @route(['/report/xlsx/<string:reportname>', '/report/xlsx/<string:reportname>/<string:docids>'],
           type='http', auth='user')
    def report_xlsx(self, reportname, docids=None, **data):
        # استدعاء التقرير
        report_obj = request.env['ir.actions.report']._get_report_from_name(reportname)

        # إعداد السياق
        context = dict(request.env.context)

        # تحويل docids إلى أرقام
        if docids:
            docids = [int(i) for i in docids.split(',')]

        # تحليل البيانات القادمة من الواجهة
        if data.get('options'):
            data.update(json.loads(data.pop('options')))
        if data.get('context'):
            ctx = json.loads(data['context'])
            ctx.pop('lang', None)  # إزالة اللغة لتجنب تعارض
            context.update(ctx)

        # توليد ملف XLSX
        xlsx_content = report_obj.with_context(context).render_xlsx(docids, data=data)[0]

        # تحديد اسم الملف
        report_name = report_obj.report_file or "report"
        if report_obj.print_report_name and docids and len(docids) == 1:
            obj = request.env[report_obj.model].browse(docids[0])
            report_name = safe_eval(report_obj.print_report_name, {'object': obj, 'time': time})

        # إعداد الرد
        headers = [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Length', str(len(xlsx_content))),
            ('Content-Disposition', content_disposition(report_name + '.xlsx'))
        ]
        return request.make_response(xlsx_content, headers=headers)
