/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
let iframeForReport;

function printPdf(url, callback) {
    let iframe = iframeForReport;
    if (!iframe) {
        iframe = iframeForReport = document.createElement('iframe');
        iframe.className = 'pdfIframe'
        document.body.appendChild(iframe);
        iframe.style.display = 'none';
        iframe.onload = function () {
            setTimeout(function () {
                iframe.focus();
                iframe.contentWindow.print();
                URL.revokeObjectURL(url)
                callback();
            }, 1);
        };
    }
    iframe.src = url;
}

function getReportUrl(action, type) {
    let url = `/report/${type}/${action.report_name}`;
    const actionContext = action.context || {};
    if (action.data && JSON.stringify(action.data) !== "{}") {
        const options = encodeURIComponent(JSON.stringify(action.data));
        const context = encodeURIComponent(JSON.stringify(actionContext));
        url += `?options=${options}&context=${context}`;
    } else {
        if (actionContext.active_ids) {
            url += `/${actionContext.active_ids.join(",")}`;
        }
        if (type === "html") {
             const context = encodeURIComponent(JSON.stringify(userContext));
            url += `?context=${context}`;
        }
    }
    return url;
}

let wkhtmltopdfStateProm;

registry
.category("ir.actions.report handlers")
.add("pdf_report_options_handler", async function (action, options, env) {
    let { is_print_preview, report_type } = action;
        is_print_preview = await env.services.orm.call(
        "ir.actions.report",
        "get_report_print_preview",
        [[action.id]]
    );
    if (report_type !== "qweb-pdf" || is_print_preview != true)
        return false;
    if (!wkhtmltopdfStateProm) {
        wkhtmltopdfStateProm = rpc("/report/check_wkhtmltopdf");
    }
    const state = await wkhtmltopdfStateProm;
    if (state === "upgrade" || state === "ok") {

        const url = getReportUrl(action, "pdf");
        if (is_print_preview == true) {
            env.services.ui.block();
            printPdf(url, () => {
                env.services.ui.unblock();
            });
        }
        return true;
    } else {
         return this._super.apply(this, arguments);
    }
})




