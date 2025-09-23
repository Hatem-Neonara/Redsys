from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta


class EtatAvancesMensuelles(models.Model):
    _name = 'etat.avances.mensuelles'
    _description = 'État d\'Avances Mensuelles'
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

    name = fields.Char(string='Référence', readonly=True, default=lambda self: 'Av/')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('salary.advance.report.seq') or ' '
        res_id = super(EtatAvancesMensuelles, self).create(vals)
        return res_id

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('close', 'Verrouiller'),
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
    journal_avances_line_ids = fields.One2many('etat.avances.mensuelles.line', 'etat_avances_mensuelles_id',
                                               string='Lignes des Avances', readonly=True)
    is_description_amount_empty = fields.Boolean(string="Is Description Amount Empty", default=False)

    def action_manual_state_change(self):
        for record in self:
            record.state = 'draft'

    logo = fields.Binary(string='Logo', related='company_id.logo',
                         store=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    def action_close(self):
        for record in self:
            record.state = 'close'
        return True

    def action_unlock(self):
        """Déverrouille un journal de paie précédemment verrouillé"""
        for record in self:
            record.state = 'confirmed'
        return True

    def generate_avances_lines(self):
        """ Generate the advances lines based on salary advances with date_retenu in the selected month """
        try:
            mois = int(self.mois)
            annee = int(self.annee)
        except ValueError:
            raise UserError("Le mois et l'année doivent être des entiers valides.")

        if not mois or not annee:
            raise UserError("Le mois et l'année doivent être définis pour générer les lignes d'avances.")

        # Use datetime to get the first and last day of the month
        date_from = date(annee, mois, 1)

        # Get the last day of the month
        if mois == 12:
            date_to = date(annee + 1, 1, 1) - timedelta(days=1)
        else:
            date_to = date(annee, mois + 1, 1) - timedelta(days=1)

        # Create base domain for salary advances
        domain = [
            ('date_retenu', '>=', date_from),
            ('date_retenu', '<=', date_to),
            ('state', '=', 'approve')  # Only approved advances
        ]

        # Add employee filter if an employee is selected
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))

        # Fetch salary advances for the given month based on date_retenu
        valid_advances = self.env['salary.advance'].search(domain)

        # Remove all existing lines
        self.journal_avances_line_ids.unlink()

        # Variable to track if any description_amount is zero or empty
        is_description_amount_empty = False

        # Create new advance lines based on the salary advances
        for advance in valid_advances:
            # Prepare values for the advance line
            values = {
                'etat_avances_mensuelles_id': self.id,
                'employe_id': advance.employee_id.id,
                'matricule': advance.employee_id.identification_id,
                'description': 'Avance sur Salaire',
                'description_amount': advance.advance,
                'department': advance.department.name if advance.department else '',
                'date_avance': advance.date,
                'date_retenu': advance.date_retenu,
                'paye': advance.paid
            }

            # Check if amount is zero
            if advance.advance == 0 or advance.advance is None:
                is_description_amount_empty = True

            # Create new line
            self.env['etat.avances.mensuelles.line'].create(values)

        # Update the parent model's state and boolean field
        self.write({
            'state': 'confirmed',
            'is_description_amount_empty': is_description_amount_empty
        })

    def update(self):
        """
        Update advances report by regenerating lines for the current month and year
        """
        self.ensure_one()
        if self.state == 'confirmed':
            try:
                mois = int(self.mois)
                annee = int(self.annee)
            except ValueError:
                raise UserError("Le mois et l'année doivent être des entiers valides.")

            if not mois or not annee:
                raise UserError("Le mois et l'année doivent être définis pour générer les lignes d'avances.")

            date_from = date(annee, mois, 1)

            # Get the last day of the month
            if mois == 12:
                date_to = date(annee + 1, 1, 1) - timedelta(days=1)
            else:
                date_to = date(annee, mois + 1, 1) - timedelta(days=1)

            # Create base domain for salary advances
            domain = [
                ('date_retenu', '>=', date_from),
                ('date_retenu', '<=', date_to),
                ('state', '=', 'approve')  # Only approved advances
            ]

            # Add employee filter if an employee is selected
            if self.employee_id:
                domain.append(('employee_id', '=', self.employee_id.id))

            # Fetch salary advances
            valid_advances = self.env['salary.advance'].search(domain)

            # Delete all existing lines first
            self.journal_avances_line_ids.unlink()

            # Variable to track if any description_amount is zero or empty
            is_description_amount_empty = False

            # Create new advance lines
            for advance in valid_advances:
                values = {
                    'etat_avances_mensuelles_id': self.id,
                    'employe_id': advance.employee_id.id,
                    'matricule': advance.employee_id.identification_id,
                    'description': 'Avance sur Salaire',
                    'description_amount': advance.advance,
                    'department': advance.department.name if advance.department else '',
                    'date_avance': advance.date,
                    'date_retenu': advance.date_retenu,
                    'paye': advance.paid
                }

                if advance.advance == 0 or advance.advance is None:
                    is_description_amount_empty = True

                self.env['etat.avances.mensuelles.line'].create(values)

            # Update the parent model's boolean field
            self.write({
                'is_description_amount_empty': is_description_amount_empty
            })

            # Return a client action to refresh the view
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return True


    @api.depends('journal_avances_line_ids.description_amount')
    def _compute_total_description_amount(self):
        for record in self:
            record.total_description_amount = sum(
                line.description_amount for line in record.journal_avances_line_ids
            )

    total_description_amount = fields.Float(
        string='Total Montant Description',
        compute='_compute_total_description_amount',
        store=True
    )


class EtatAvancesMensuellesLine(models.Model):
    _name = 'etat.avances.mensuelles.line'
    _description = 'Ligne d\'Avances Mensuelles'
    _order = 'matricule asc'

    etat_avances_mensuelles_id = fields.Many2one('etat.avances.mensuelles', string='État d\'Avances Mensuelles',
                                                 required=True, ondelete='cascade')
    employe_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Nom et Prénom',
        required=True
    )
    matricule = fields.Char(
        string='Matricule',
        related='employe_id.identification_id',
        store=True,
        readonly=True
    )
    description = fields.Char(string='Description')
    description_amount = fields.Float(string='Montant Description')
    nbj = fields.Float(string='Nombre de Jours', )
    salaire_base = fields.Float(string='Salaire de Base', )
    salaire_brute = fields.Float(string='Salaire Brut', )
    cnss = fields.Float(string='CNSS', )
    cavis = fields.Float(string='CAVIS', )  # Updated field name
    total_charge = fields.Float(
        string='Total Charges',
        compute='_compute_total_charge',
        store=True
    )
    salaire_imposable = fields.Float(string='Salaire Imposable')
    impot = fields.Float(string='Impôt')
    assurance_group = fields.Float(string='Assurance Groupe')
    pret = fields.Float(string='Prêt', required=False)
    avance = fields.Float(string='Avance', required=False)
    cnss_patronale = fields.Float(string='CNSS Patronale')
    total_charge_patronale = fields.Float(string='Total Charge Patronale')
    accident_travail = fields.Float(string='Accident de Travail')
    tfp = fields.Float(string='TFP')
    assurance_group_patr = fields.Float(string='Assurance Groupe Patronale')

    @api.depends('cnss', 'cavis')
    def _compute_total_charge(self):
        for record in self:
            record.total_charge = record.cnss + record.cavis

    department = fields.Char(string='Département')
    date_avance = fields.Date(string='Date d\'avance')
    date_retenu = fields.Date(string='Date de retenu')
    paye = fields.Boolean(string='Payé')
