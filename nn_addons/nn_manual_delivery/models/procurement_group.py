from odoo import fields, models


class ProcurementGroup(models.Model):
    _inherit = "procurement.group"

    date_planned = fields.Date()
