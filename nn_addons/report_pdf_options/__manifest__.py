# -*- coding: utf-8 -*-
{
    'name': 'Pdf report options',
    'summary': """shows a modal window with options for printing, downloading or opening pdf reports""",
    'description': """
        Choose one of the following options when printing a pdf report:
        - print. print the pdf report directly with the browser
        - download. download the pdf report on your computer
        - open. open the pdf report in a new tab
        You can also set a default options for each report
    """,
    'author': 'Neonara',
    'category': 'Productivity',
    'depends': ['web'],
    'data': [
        'views/ir_actions_report.xml',
    ],
    'images': ['static/description/banner.png'],

    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'report_pdf_options/static/src/js/PdfOptionsModal.js',
            'report_pdf_options/static/src/js/qwebactionmanager.js',
            'report_pdf_options/static/src/**/*.xml'
        ]
    }
}
