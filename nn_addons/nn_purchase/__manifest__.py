{
    'name': "NeoNara Purchase",
    'author': 'NeoNara',
    'category': '',
    'summary': """""",
    'sequence': 1,
    'license': 'AGPL-3',
    'website': 'www.neonara.digital',
    'description': "Module NeonNara ",
    'version': '17.0',

    'depends': ['base', 'purchase'],

    'data': [
        'views/purchase_price_history.xml',
             ],

    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}