from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    manual_delivery = fields.Boolean(string="Use Manual Delivery",
                                     default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
                                         'stock.manual_delivery') == 'True',
                                     help="If enabled, the deliveries are not created at SO confirmation. "
                                          "You need to use the Create Delivery button in order to reserve "
                                          "and ship the goods.",)

    has_pending_delivery = fields.Boolean(
        string="Attente Livraison",
        compute="_compute_delivery_pending",
    )

    def _compute_delivery_pending(self):
        for rec in self:
            lines_pending = rec.order_line.filtered(
                lambda x: x.product_id.type != "service" and x.qty_to_procure > 0
            )
            rec.has_pending_delivery = bool(lines_pending)

    def action_manual_delivery_wizard(self):
        self.ensure_one()
        action = self.env.ref("nn_manual_delivery.action_wizard_manual_delivery")
        [action] = action.read()
        action["context"] = {"default_carrier_id": self.carrier_id.id}
        return action

    @api.constrains("manual_delivery")
    def _check_manual_delivery(self):
        if any(rec.state not in ["draft", "sent"] for rec in self):
            raise UserError(
                _(
                    "You can only change to/from manual delivery"
                    " in a quote, not a confirmed order"
                )
            )
