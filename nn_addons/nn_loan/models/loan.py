

from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class HrLoan(models.Model):
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Loan Request"
    _check_company_auto = True

    @api.model
    def default_get(self, field_list):
        result = super(HrLoan, self).default_get(field_list)
        if result.get('user_id'):
            ts_user_id = result['user_id']
        else:
            ts_user_id = self.env.context.get('user_id', self.env.user.id)
        result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', ts_user_id)], limit=1).id
        return result

    def compute_loan_amount(self):
        total_paid = 0.0
        for loan in self:
            for line in loan.loan_lines:
                if line.paid:
                    total_paid += line.amount
            balance_amount = loan.loan_amount - total_paid
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid

    @api.depends('loan_lines.paid', 'loan_lines')
    def _compute_payment_status(self):
        for loan in self:
            if not loan.loan_lines:
                loan.payment_status = 'unpaid'
            elif all(line.paid for line in loan.loan_lines):
                loan.payment_status = 'paid'
            elif any(line.paid for line in loan.loan_lines):
                loan.payment_status = 'both'
            else:
                loan.payment_status = 'unpaid'

    name = fields.Char(string="Code Prêt", default="/", readonly=True, help="Code of the loan")
    date = fields.Date(string="Date", default=fields.Date.today(), readonly=True, help="Date")
    employee_id = fields.Many2one('hr.employee', string="Employée", required=True, help="Employee")
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Départment", help="Employee")
    installment = fields.Integer(string="Nbr d'Echéances", default=1, help="Number of installments")
    payment_date = fields.Date(string="Date Début Paiement", required=True, default=fields.Date.today(), help="Date of "
                                                                                                             "the "
                                                                                                             "paymemt")
    loan_lines = fields.One2many('hr.loan.line', 'loan_id', string="Loan Line", index=True)
    company_id = fields.Many2one('res.company', 'Société', readonly=True, help="Company",
                                 default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Devise', required=True, help="Currency",
                                  default=lambda self: self.env.user.company_id.currency_id)
    job_position = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Poste",
                                   help="Job position")
    loan_amount = fields.Float(string="Montant Prêt", required=True, help="Loan amount")
    total_amount = fields.Float(string="Montant Total", store=True, readonly=True, compute='compute_loan_amount',
                                help="Total loan amount")
    balance_amount = fields.Float(string="Balance", store=True, compute='compute_loan_amount', help="Balance amount")
    total_paid_amount = fields.Float(string="Montant Total Payé", store=True, compute='compute_loan_amount',
                                     help="Total paid amount")

    month = fields.Selection([
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
                ('12', 'Décembre')
            ], string='Mois')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('waiting_approval_1', 'Attente Approbation'),
        ('approve', 'Approuvé'),
        ('refuse', 'Refusé'),
        ('cancel', 'Annulé'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )

    payment_status = fields.Selection([
            ('paid', 'Payé'),
            ('unpaid', 'Non Payé'),
            ('both', 'Payé + Non Payé')
        ], string='Statut de paiement', default='both')


    @api.model
    def create(self, values):
        loan_count = self.env['hr.loan'].search_count([
            ('employee_id', '=', values['employee_id']),
            ('state', '=', 'approve'),
            ('balance_amount', '!=', 0)
        ])

        if loan_count:
            raise ValidationError(_("The employee has already a pending installment"))

        # SÉCURITÉ : Vérifier l'unicité du nom généré
        if not values.get('name') or values.get('name') == '/':
            max_attempts = 10
            attempt = 0

            while attempt < max_attempts:
                sequence = self.env['ir.sequence'].next_by_code('hr.loan.seq')

                # Vérifier si ce nom existe déjà
                existing = self.env['hr.loan'].search_count([('name', '=', sequence)])
                if not existing:
                    values['name'] = sequence
                    break
                attempt += 1

            if attempt >= max_attempts:
                # Solution de fallback
                import uuid
                values['name'] = f'Prêt/{str(uuid.uuid4())[:8]}'

        res = super(HrLoan, self).create(values)
        return res

    def compute_installment(self):
        """This automatically create the installment the employee need to pay to
        company based on payment start date and the no of installments.
            """
        for loan in self:
            loan.loan_lines.unlink()
            date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
            amount = loan.loan_amount / loan.installment
            for i in range(1, loan.installment + 1):
                self.env['hr.loan.line'].create({
                    'date': date_start,
                    'amount': amount,
                    'employee_id': loan.employee_id.id,
                    'loan_id': loan.id})
                date_start = date_start + relativedelta(months=1)
            loan.compute_loan_amount()
        return True

    def action_refuse(self):
        return self.write({'state': 'refuse'})

    def action_submit(self):
        for rec in self:
            if rec.loan_amount > 0:
                rec.write({'state': 'waiting_approval_1'})
            else:
                raise UserError(_("Veuillez introduire un montant pour le prêt."))

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_approve(self):
        for data in self:
            if not data.loan_lines:
                raise ValidationError(_("Please Compute installment"))
            else:
                self.write({'state': 'approve'})

    def unlink(self):
        for loan in self:
            if loan.state not in ('draft', 'cancel'):
                raise UserError(
                    'Vous ne pouvez pas supprimer un prêt qui n\'est pas à l\'état de brouillon ou annulé')
        return super(HrLoan, self).unlink()

    def report_installment(self, installment_line_id):
        """
        Cette méthode permet de reporter une échéance non payée au mois suivant,
        et décale également toutes les échéances suivantes.

        :param installment_line_id: ID de la ligne d'échéance à reporter
        :return: True si succès
        """
        self.ensure_one()
        if self.state != 'approve':
            raise UserError(_("Vous ne pouvez reporter une échéance que pour un prêt approuvé."))

        # Récupérer la ligne d'échéance à reporter
        installment_line = self.env['hr.loan.line'].browse(installment_line_id)

        if not installment_line or installment_line.loan_id.id != self.id:
            raise ValidationError(_("Échéance non trouvée ou n'appartient pas à ce prêt."))

        if installment_line.paid:
            raise ValidationError(_("Impossible de reporter une échéance déjà payée."))

        # Récupérer toutes les échéances non payées dans l'ordre de date
        unpaid_lines = self.loan_lines.filtered(lambda line: not line.paid).sorted(key=lambda line: line.date)

        if not unpaid_lines or installment_line.id != unpaid_lines[0].id:
            raise ValidationError(_("Vous ne pouvez reporter que l'échéance non payée la plus ancienne."))

        # Calculer la nouvelle date pour chaque échéance (+ 1 mois)
        for line in unpaid_lines:
            old_date = datetime.strptime(str(line.date), '%Y-%m-%d')
            new_date = old_date + relativedelta(months=1)
            line.write({'date': new_date})

        # Recalculer les montants
        self.compute_loan_amount()

        # Enregistrer l'action dans l'historique du prêt
        msg = _("Échéance du %s reportée au %s") % (
            installment_line.date - relativedelta(months=1),
            installment_line.date
        )
        self.message_post(body=msg)

        return True

    @api.depends('payment_date')
    def _compute_month(self):
        for loan in self:
            if loan.payment_date:
                loan.month = loan.payment_date.strftime('%B %Y')
            else:
                loan.month = False


class InstallmentLine(models.Model):
    _name = "hr.loan.line"
    _description = "Installment Line"
    _check_company_auto = True


    date = fields.Date(string="Date Paiement", required=True, help="Date of the payment")
    employee_id = fields.Many2one('hr.employee', string="Employée", help="Employee")
    company_id = fields.Many2one('res.company', 'Société', readonly=True, help="Company",
                                 default=lambda self: self.env.user.company_id)
    amount = fields.Float(string="Montant", required=True, help="Amount", digits='Product Price')
    paid = fields.Boolean(string="Payé", help="Paid")
    loan_id = fields.Many2one('hr.loan', string="Ref Prêt.", help="Loan")
    payslip_id = fields.Many2one('hr.payslip', string="Ref Bulletin", help="Payslip")

    def report_installment_action(self):
        """
        Méthode appelée par le bouton pour reporter l'échéance
        """
        self.ensure_one()
        if self.paid:
            raise ValidationError(_("Impossible de reporter une échéance déjà payée."))

        return self.loan_id.report_installment(self.id)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _compute_employee_loans(self):
        """This compute the loan amount and total loans count of an employee.
            """
        self.loan_count = self.env['hr.loan'].search_count([('employee_id', '=', self.id)])

    loan_count = fields.Integer(string="Prêt", compute='_compute_employee_loans')
