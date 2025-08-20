from odoo import models, fields, api
from odoo.exceptions import UserError



class EtatAvancesNonPayees(models.Model):
    _name = 'etat.avances.non.payees'
    _description = 'État d\'Avances Non Payees'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    name = fields.Char(string='Référence', readonly=True, default=lambda self: 'ANP/')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
    ], string="Statut", default='draft')

    date_from = fields.Date(string='Date Début', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='Date Fin', required=True, default=fields.Date.context_today)

    avances_line_ids = fields.One2many('etat.avances.non.payees.line', 'etat_avances_id',
                                       string='Lignes des Avances Non Payées', readonly=True)

    company_id = fields.Many2one('res.company', string='Société',
                                 default=lambda self: self.env.company)
    logo = fields.Binary(string='Logo', related='company_id.logo',
                         store=True)

    total_amount = fields.Float(string='Montant Total',
                                compute='_compute_total_amount',
                                store=True)

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('unpaid.advance.report.seq') or 'ANP/'
        return super(EtatAvancesNonPayees, self).create(vals)

    @api.depends('avances_line_ids.montant')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(line.montant for line in record.avances_line_ids)

    def generate_lines(self):
        """Générer les lignes d'avances non payées"""
        self.ensure_one()

        # Vérifier les dates
        if self.date_from > self.date_to:
            raise UserError("La date de début doit être antérieure à la date de fin")

        # Rechercher les avances approuvées mais non payées
        advances = self.env['salary.advance'].search([
            ('state', '=', 'approve'),
            ('paid', '=', False),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ])

        # Supprimer les lignes existantes
        self.avances_line_ids.unlink()

        # Créer les nouvelles lignes
        for advance in advances:
            self.env['etat.avances.non.payees.line'].create({
                'etat_avances_id': self.id,
                'employee_id': advance.employee_id.id,
                'matricule': advance.employee_id.identification_id,
                'department_id': advance.department.id,
                'date_avance': advance.date,
                'date_retenu': advance.date_retenu,
                'montant': advance.advance,
                'advance_id': advance.id
            })

        self.state = 'confirmed'
        return True

    def action_draft(self):
        """Remettre l'état en brouillon"""
        self.state = 'draft'
        return True

    def action_print_report(self):
        """Imprimer le rapport des avances non payées"""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError('Le rapport ne peut être imprimé que pour les états confirmés')
        return self.env.ref('module_name.action_report_unpaid_advances').report_action(self)


class EtatAvancesNonPayeesLine(models.Model):
    _name = 'etat.avances.non.payees.line'
    _description = 'Ligne État d\'Avances Non Payees'

    etat_avances_id = fields.Many2one('etat.avances.non.payees',
                                      string='État Avances',
                                      required=True,
                                      ondelete='cascade')

    employee_id = fields.Many2one('hr.employee',
                                  string='Employé',
                                  required=True)

    matricule = fields.Char(string='Matricule',
                            related='employee_id.identification_id',
                            store=True,
                            readonly=True)

    department_id = fields.Many2one('hr.department',
                                    string='Département')

    date_avance = fields.Date(string='Date Avance')
    date_retenu = fields.Date(string='Date Retenue')
    montant = fields.Float(string='Montant')

    advance_id = fields.Many2one('salary.advance',
                                 string='Avance Salariale',
                                 readonly=True)

    days_pending = fields.Integer(string='Jours en Attente',
                                  compute='_compute_days_pending',
                                  store=True)

    @api.depends('date_avance')
    def _compute_days_pending(self):
        today = fields.Date.today()
        for record in self:
            if record.date_avance:
                delta = today - record.date_avance
                record.days_pending = delta.days
            else:
                record.days_pending = 0

