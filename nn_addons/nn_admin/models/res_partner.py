from odoo import api, fields, models, tools, SUPERUSER_ID, _, Command
from odoo.exceptions import RedirectWarning, UserError, ValidationError


class Partner(models.Model):
    _inherit = 'res.partner'

    is_customer = fields.Boolean(string='Customer')
    is_supplier = fields.Boolean(string='Supplier')