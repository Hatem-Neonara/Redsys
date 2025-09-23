{
    'name': "NN Loan",
    'author': 'NN Tech',
    'category': 'Loan',
    'summary': "Module de gestion des prets pour NN Technologies",
    'license': 'AGPL-3',
    'website': 'https://www.bmgtech.tn',
    'description': "Modules NN Technologies Loan",
    'version': '17.0.1.0',
    'depends': [

        'base',
        'report_xlsx',
        'hr',
        'hr_contract',

    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'report/loan_report.xml',
        'report/etat_prets_mensuels.xml',

        'views/loan.xml',
        'views/etat_prets_mensuels.xml',

    ],

    'images': ['static/description/banner.png'],

    'installable': True,
    'application': True,
    'auto_install': False,
}
