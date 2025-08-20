# Copyright 2023 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SignOcaRole(models.Model):
    _name = "sign.oca.role"
    _description = "Sign Role"

    name = fields.Char(required=True, string="Nom")
    domain = fields.Char(required=True, default=[])
    partner_selection_policy = fields.Selection( string="Politique Partenaire",
        selection=[
            ("empty", "Vide"),
            ("default", "Défaut"),
            ("expression", "Expression"),
        ],
        required=True,
        default="empty",

    )
    default_partner_id = fields.Many2one(
        comodel_name="res.partner", string="Contact par défaut"
    )
    expression_partner = fields.Char(
        string="Expression", help="Example: {{object.partner_id.id}}"
    )

    @api.onchange("partner_selection_policy")
    def _onchange_partner_selection_policy(self):
        for item in self:
            if item.partner_selection_policy == "empty":
                item.default_partner_id = False
                item.expression_partner = False
            elif item.partner_selection_policy == "default":
                item.expression_partner = False
            elif item.partner_selection_policy == "expression":
                item.default_partner_id = False

    def _get_partner_from_record(self, record):
        partner = self.default_partner_id.id or False
        if self.partner_selection_policy == "expression" and record:
            res = self.env["mail.render.mixin"]._render_template(
                self.expression_partner, record._name, record.ids
            )[record.id]
            partner = int(res) if res else False
        return partner
