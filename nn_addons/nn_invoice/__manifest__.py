{
    'name': "NeoNara Invoice",
    'author': 'NeoNara',
    'category': '',
    'summary': """""",
    'license': 'AGPL-3',
    'website': 'www.neonara.digital',
    'description': "Module NeonNara ",
    'version': '17.0',

    'depends': ['base', 'account', 'sale_management'],

    'data': [
        'views/price_liste_invoice.xml',
             ],

    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    "pre_init_hook": "pre_init_hook",

}