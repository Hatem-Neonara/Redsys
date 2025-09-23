{
    "name": "NeoNara Sale Manual Delivery",
    "category": "Sale",
    'author': 'NeoNara',
    "license": "AGPL-3",
    'version': '17.0',
    'website': 'www.neonara.digital',
    "summary": "Module to create manually picking from sale order",
    "depends": ["stock_delivery", "sale_stock", "stock", "purchase_stock"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/manual_delivery.xml",
        "wizard/manual_reception.xml",
        "views/setting.xml",
        "views/sale_order.xml",
        "views/purchase_order_views.xml",
    ],

    "assets": {
        "web.assets_backend": [
            "nn_manual_delivery/static/src/**/*",
        ]
    },

    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    "pre_init_hook": "pre_init_hook",
}
