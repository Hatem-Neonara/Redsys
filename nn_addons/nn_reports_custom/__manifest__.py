{
    'name': "NeoNara - Redsys - Reports ",
    'author': 'NeoNara',
    'category': '',
    'summary': """""",
    'license': 'AGPL-3',
    'website': 'www.neonara.digital',
    'description': "Module NeonNara ",
    'version': '17.0',

    'depends': ['base', 'web', 'account', 'sale', 'purchase'],

    'data': [
        'views/res_company_view_report.xml',
        'views/account_move_view.xml',
             ],

    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}