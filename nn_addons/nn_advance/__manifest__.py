{
    'name': "NN Advance",
    'author': 'NN Tech',
    'category': 'Advance',
    'summary': "Module de gestion d'avance pour NN Technologies",
    'license': 'AGPL-3',
    'website': 'https://www.bmgtech.tn',
    'description': "Modules NN Technologies Advance",
    'version': '17.0.1.0',
    'depends': [

        'base',
        'mail',
        'report_xlsx',
        'hr',
        'hr_contract',

    ],
    'data': [
        'security/salary_advance_security.xml',
        'security/ir.model.access.csv',

        'report/analyse_reports.xml',
        'report/etat_avances_mensuelles.xml',
        'report/salary_advance_report.xml',

        'views/avance.xml',
        'views/etat_avances_mensuelles_form_tree.xml',
        'views/etat_avances_non_payees.xml',

    ],
    'images': ['static/description/banner.png'],

    'installable': True,
    'application': True,
    'auto_install': False,
}
