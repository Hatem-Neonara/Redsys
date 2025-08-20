from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_stamp_exempt = fields.Boolean(
        string="Exonéré Timbre",
        default=False,
        help="Si coché, ce partenaire est exonéré de la taxe de timbre fiscal"
    )