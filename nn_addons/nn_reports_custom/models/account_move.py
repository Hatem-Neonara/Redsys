from odoo import models, fields, api
from datetime import datetime


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_payment_delayed = fields.Boolean("Alerte de retard de paiement", compute="_compute_payment_delay")
    is_ = fields.Boolean("Alerte de retard de paiement", compute="_compute_payment_delay")

    @api.depends('invoice_date_due', 'state')
    def _compute_payment_delay(self):
        for record in self:

            if record.state == 'posted' and record.invoice_date_due:
                # Si la date d'échéance est dépassée et la facture est déjà validée
                if datetime.now() > fields.Datetime.from_string(record.invoice_date_due):
                    record.is_payment_delayed = True
                else:
                    record.is_payment_delayed = False
            else:
                record.is_payment_delayed = False
