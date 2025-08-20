{
    'name': "NeoNara Redsys CRM Workflow",
    'author': 'NeoNara',
    'category': '',
    'summary': """""",
    'license': 'AGPL-3',
    'website': 'www.neonara.digital',
    'description': "Module NeonNara ",
    'version': '17.0',

    'depends': ['stock', 'purchase', 'product', 'base', 'sale', 'crm', 'nn_reports_custom', 'sale_crm'],

    'data': [
        'security/ir.model.access.csv',
        'views/product.xml',
        'views/crm_lead.xml',
        'views/sale_quotation.xml',
        'views/taux_dd.xml',
        'data/ir_cron_data.xml',
        'views/purchase.xml',
             ],

    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}