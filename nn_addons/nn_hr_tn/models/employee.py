from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.exceptions import ValidationError

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.constrains("compte_banque")
    def check_compte_banque(self):
        for record in self:
            if record.bank_account and len(record.bank_account) != 20:
                raise ValidationError(_("Le RIB Bancaire doit contenir 20 Chiffres"))

    _sql_constraints = [
        ('num_banque_unique', 'UNIQUE(bank_account)', "Le numéro du compte bancaire doit être unique"), ]

    statut_employee = fields.Selection([
        ('permanent', 'Permanent'),
        ('contractuel', 'Contractuel'),
        ('stagiaire', 'Stagiaire'),

    ], string='Statut Employé', copy=False, index=True, tracking=True, store=True)

    num_cin = fields.Char('CIN', size=8)
    date_cin = fields.Date('Délivrée Le')

    chef_famille = fields.Boolean(default=False, string="Chef de Famille")


