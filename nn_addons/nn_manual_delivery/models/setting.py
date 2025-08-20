from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    manual_delivery = fields.Boolean(
        string="Use Manual Delivery",
        config_parameter="stock.manual_delivery",
        help="If enabled, the deliveries are not created at SO confirmation. "
             "You need to use the Create Delivery button in order to reserve and ship the goods.",
    )

    purchase_manual_delivery = fields.Boolean(string="Purchase manual delivery",
                                              config_parameter="stock.purchase_manual_delivery",)

