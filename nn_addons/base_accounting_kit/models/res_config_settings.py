from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    customer_credit_limit = fields.Boolean(string="Customer Credit Limit")

    use_anglo_saxon_accounting = fields.Boolean(
        string="Use Anglo-Saxon accounting", readonly=False,
        related='company_id.anglo_saxon_accounting')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        customer_credit_limit = params.get_param('customer_credit_limit',
                                                 default=False)
        res.update(customer_credit_limit=customer_credit_limit)
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            "customer_credit_limit",
            self.customer_credit_limit)
