{
    'name': 'Odoo Direct Print',
    'version': '18.3',
    'category': 'Stock',
    'summary': 'Instant Report Printing, Direct Print Functionality, One-Click Printing, Direct Print Popup, Automated Report Printing, Print Reports Directly, Seamless Direct Printing, Direct Printing Without Download, Quick Print Option, Print Report Popup Control,Direct print, print, auto print,advance print,This application is used to print the report directly without downloading the PDF user have the easy access to the report print.Direct Print report. Print reports directly without downloading PDFs, providing easy and instant access to printed reports.direct print, report printing, Odoo, direct report print, no download print, print settings',
    
    'description': 'This Odoo module enables users to print reports directly from the system without needing to download them as PDFs. With features like direct printing, customizable report settings, preview options, and compatibility with both community and enterprise editions, it streamlines the report printing process and eliminates unnecessary steps. The module does not require additional hardware like the Odoo IoT box, making it cost-effective and user-friendly.',
 
    'author': 'INKERP',
    'website': "www.inkerp.com",
    'depends': ['mail','web'],
    'data': [
        'views/ir_action_report_view.xml',
        'views/res_config_settings_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'eg_direct_print_report/static/src/js/qwebactionmanager.js',
        ],
    },
    'post_init_hook': '_set_direct_print_post_init',
    'images': ['static/description/banner.gif'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': '15.00',
    'currency': 'EUR',
}
