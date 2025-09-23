{
    'name': "NN HR",
    'author': 'NN Tech',
    'category': '',
    'summary': """""",
    'license': 'AGPL-3',
    'website': 'www.bmgtech.tn',
    'description': "Modules BMG Technologies HR",
    'version': '17.0',

    'depends': ['base', 'hr', 'hr_contract', 'hr_recruitment', 'nn_admin',],

    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'views/contract_employee.xml',
        'views/document_management.xml',
        'views/skill_qualification.xml',
        'views/duree_service.xml',
        'views/multi_post.xml',
        'views/employee.xml',

    ],

    'images': ['static/description/banner.png'],

    'installable': True,
    'application': True,
    'auto_install': False,
}
