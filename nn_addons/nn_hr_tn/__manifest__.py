{
    'name': "NN HR TN",
    'author': 'NN Tech',
    'category': '',
    'summary': """""",
    'license': 'AGPL-3',
    'website': 'www.bmgtech.tn',
    'description': "Modules BMG Technologies HR TN ",
    'version': '17.0',

    'depends': ['base', 'hr', 'hr_contract', 'hr_recruitment', 'nn_hr'],

    'data': [
        'security/ir.model.access.csv',
        'views/employee.xml',

    ],

    'images': ['static/description/banner.png'],

    'installable': True,
    'application': True,
    'auto_install': False,
}
