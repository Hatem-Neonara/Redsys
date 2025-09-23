from odoo import api, fields, models, tools, _

class Company(models.Model):
    _inherit = "res.company"


    company_bank = fields.Many2one('company.bank', string="Company Bank", domain="[('company_id', '=', id)]")
    bank_company_id = fields.Char(string="Bank", related="company_bank.name")
    bank_company_account = fields.Char(string="Bank Account", related="company_bank.bank_company_account")
    agence_id = fields.Char(string="Agence", related="company_bank.agence_id")

# Créer les séquences automatique lors de la création d'une nouvelle société

    @api.model
    def create(self, vals):
        company = super().create(vals)
        company._duplicate_default_sequences()
        return company

    def _duplicate_default_sequences(self):
        IrSequence = self.env['ir.sequence']
        source_sequences = IrSequence.search([])

        for sequence in source_sequences:
            if not sequence.code or sequence.code == 'stock.scrap':
                continue
            already_exists = IrSequence.search_count([
                ('code', '=', sequence.code),
                ('company_id', '=', self.id)
            ])
            if not already_exists:
                sequence.copy({
                    'name': f"{sequence.name} ({self.name})",
                    'company_id': self.id
                })

    purchase_sign = fields.Binary(string="Signature Achat")
    sale_sign = fields.Binary(string="Signature Vente")