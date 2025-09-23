from odoo import api, fields, models, tools, _

class CompanyBank(models.Model):
    _name = 'company.bank'
    _check_company_auto = True


    name = fields.Char(string="Bank")
    bank_company_account = fields.Char(string="Bank Account")
    agence_id = fields.Char(string="Agence")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    iban = fields.Char(string="Code IBAN")