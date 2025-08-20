# Copyright 2024 ForgeFlow S.L. (http://www.forgeflow.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sign_oca_send_sign_request_copy = fields.Boolean(
        string="Envoyer aux signataires une copie du document final signé",
        help="Une fois la demande signée par tous les signataires, une copie du document final leur sera envoyée..",
    )
