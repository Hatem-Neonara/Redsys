from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta


class EtatPretsMensuels(models.Model):
    _name = 'etat.prets.mensuels'
    _description = 'État des Prêts Mensuels'
    _check_company_auto = True

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=False,
        help="Optionnel: Sélectionnez un employé pour filtrer les prêts"
    )

    @api.model
    def _get_years(self):
        current_year = datetime.now().year
        years = []
        # Générer une liste d'années (5 ans avant l'année courante jusqu'à 5 ans après)
        for year in range(current_year - 5, current_year + 6):
            years.append((str(year), str(year)))
        return years

    name = fields.Char(string='Référence', readonly=True, default=lambda self: 'Pr/')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('loan.report.seq') or ' '
        res_id = super(EtatPretsMensuels, self).create(vals)
        return res_id

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
    ], string="Statut", default='draft')

    mois = fields.Selection(
        selection=[
            ('01', 'Janvier'),
            ('02', 'Février'),
            ('03', 'Mars'),
            ('04', 'Avril'),
            ('05', 'Mai'),
            ('06', 'Juin'),
            ('07', 'Juillet'),
            ('08', 'Août'),
            ('09', 'Septembre'),
            ('10', 'Octobre'),
            ('11', 'Novembre'),
            ('12', 'Décembre'),
        ],
        string='Mois',
        required=True
    )

    annee = fields.Selection(
        selection='_get_years',
        string='Année',
        required=True,
        default=lambda self: str(datetime.now().year)
    )

    journal_prets_line_ids = fields.One2many('etat.prets.mensuels.line', 'etat_prets_mensuels_id',
                                             string='Lignes des Prêts', readonly=True)

    is_amount_empty = fields.Boolean(string="Is Amount Empty", default=False)

    logo = fields.Binary(string='Logo', related='company_id.logo', store=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)



    def generate_prets_lines(self):
        """Generate the loan lines based on loan installments for the selected month"""
        try:
            mois = int(self.mois)
            annee = int(self.annee)
        except ValueError:
            raise UserError("Le mois et l'année doivent être des entiers valides.")

        if not mois or not annee:
            raise UserError("Le mois et l'année doivent être définis pour générer les lignes de prêts.")

        # Get the first and last day of the month
        date_from = date(annee, mois, 1)
        if mois == 12:
            date_to = date(annee + 1, 1, 1) - timedelta(days=1)
        else:
            date_to = date(annee, mois + 1, 1) - timedelta(days=1)

        # Create the domain for loan installments
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('loan_id.state', '=', 'approve')  # Only approved loans
        ]

        # Add employee filter if an employee is selected
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))

        # Fetch loan installments for the given month
        valid_installments = self.env['hr.loan.line'].search(domain)

        # Remove existing loan lines
        self.journal_prets_line_ids.unlink()

        is_amount_empty = False

        # Create new loan lines
        for installment in valid_installments:
            loan = installment.loan_id
            values = {
                'etat_prets_mensuels_id': self.id,
                'employe_id': installment.employee_id.id,
                'matricule': installment.employee_id.identification_id,
                'description': f'Échéance Prêt {loan.name}',
                'montant_echeance': installment.amount,
                'department': loan.department_id.name if loan.department_id else '',
                'date_pret': loan.date,
                'date_echeance': installment.date,
                'paye': installment.paid,
                'montant_total_pret': loan.loan_amount,
                'nbr_echeances': loan.installment,
                'montant_restant': loan.balance_amount
            }

            if installment.amount == 0 or installment.amount is None:
                is_amount_empty = True

            self.env['etat.prets.mensuels.line'].create(values)

        self.write({
            'state': 'confirmed',
            'is_amount_empty': is_amount_empty
        })

    def update(self):
        """Update loans report by regenerating lines for the current month"""
        self.ensure_one()
        if self.state == 'confirmed':
            try:
                mois = int(self.mois)
                annee = int(self.annee)
            except ValueError:
                raise UserError("Le mois et l'année doivent être des entiers valides.")

            if not mois or not annee:
                raise UserError("Le mois et l'année doivent être définis pour générer les lignes de prêts.")

            # Get the first and last day of the month
            date_from = date(annee, mois, 1)
            if mois == 12:
                date_to = date(annee + 1, 1, 1) - timedelta(days=1)
            else:
                date_to = date(annee, mois + 1, 1) - timedelta(days=1)

            # Create the domain for loan installments
            domain = [
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('loan_id.state', '=', 'approve')  # Only approved loans
            ]

            # Add employee filter if an employee is selected
            if self.employee_id:
                domain.append(('employee_id', '=', self.employee_id.id))

            # Fetch loan installments for the given month
            valid_installments = self.env['hr.loan.line'].search(domain)

            # Remove existing loan lines
            self.journal_prets_line_ids.unlink()

            is_amount_empty = False

            # Create new loan lines
            for installment in valid_installments:
                loan = installment.loan_id
                values = {
                    'etat_prets_mensuels_id': self.id,
                    'employe_id': installment.employee_id.id,
                    'matricule': installment.employee_id.identification_id,
                    'description': f'Échéance Prêt {loan.name}',
                    'montant_echeance': installment.amount,
                    'department': loan.department_id.name if loan.department_id else '',
                    'date_pret': loan.date,
                    'date_echeance': installment.date,
                    'paye': installment.paid,
                    'montant_total_pret': loan.loan_amount,
                    'nbr_echeances': loan.installment,
                    'montant_restant': loan.balance_amount
                }

                if installment.amount == 0 or installment.amount is None:
                    is_amount_empty = True

                self.env['etat.prets.mensuels.line'].create(values)

            # Update the boolean field
            self.write({
                'is_amount_empty': is_amount_empty
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return True

    @api.depends('journal_prets_line_ids.montant_echeance')
    def _compute_total_montant(self):
        for record in self:
            record.total_montant = sum(
                line.montant_echeance for line in record.journal_prets_line_ids
            )

    total_montant = fields.Float(
        string='Total Montant Échéances',
        compute='_compute_total_montant',
        store=True
    )


class EtatPretsMensuelsLine(models.Model):
    _name = 'etat.prets.mensuels.line'
    _description = "Ligne d'État des Prêts Mensuels"
    _order = 'matricule asc'
    _check_company_auto = True

    etat_prets_mensuels_id = fields.Many2one('etat.prets.mensuels', string='État des Prêts Mensuels',
                                             required=True, ondelete='cascade')
    employe_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Nom et Prénom',
        required=True
    )
    company_id = fields.Many2one('res.company', 'Société', readonly=True, help="Company",
                                 default=lambda self: self.env.user.company_id)
    matricule = fields.Char(
        string='Matricule',
        related='employe_id.identification_id',
        store=True,
        readonly=True
    )
    description = fields.Char(string='Description')
    montant_echeance = fields.Float(string='Montant Échéance')
    montant_total_pret = fields.Float(string='Montant Total Prêt')
    nbr_echeances = fields.Integer(string='Nombre Échéances')
    montant_restant = fields.Float(string='Montant Restant')
    department = fields.Char(string='Département')
    date_pret = fields.Date(string='Date Prêt')
    date_echeance = fields.Date(string="Date d'Échéance")
    paye = fields.Boolean(string='Payé')