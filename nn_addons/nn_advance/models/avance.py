# -*- coding: utf-8 -*-
import time
from datetime import datetime
from odoo import fields, models, api, _
from odoo import exceptions
from odoo.exceptions import UserError

class SalaryAdvancePayment(models.Model):
    _name = "salary.advance"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Salary Advance"
    _check_company_auto = True


    name = fields.Char(string='Nom', readonly=True, default=lambda self: 'Av/')
    employee_id = fields.Many2one('hr.employee', string='Employée', required=True, help="Employee")
    date = fields.Date(string='Date d\'avance', required=True, default=lambda self: fields.Date.today(), help="Submit date")
    reason = fields.Text(string='Raison', help="Reason")
    currency_id = fields.Many2one('res.currency', string='Devise', required=True, readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', string='Société', required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id)
    advance = fields.Float(string='Avance', required=True, digits='Payroll')
    date_retenu = fields.Date(string='Date de retenu', required=True, default=lambda self: fields.Date.today(),
                       help="Submit date")
    payment_method = fields.Many2one('account.journal', string='Mode de Paiement')
    exceed_condition = fields.Boolean(string='Dépasser le Maximum',
                                      help="The Advance is greater than the maximum percentage in salary structure")
    department = fields.Many2one('hr.department', string='Départment', readonly=True)
    state = fields.Selection([('draft', 'Brouillon'),
                              ('waiting_approval', 'En Attente d\'Approbation'),
                              ('approve', 'Approuvé'),
                              ('cancel', 'Annulé'),
                              ('reject', 'Rejeté')], string='Status', default='draft', tracking=True)

    employee_contract_id = fields.Many2one('hr.contract', string='Contrat', readonly=True)
    paid = fields.Boolean(string="Payé")
    logo = fields.Binary(string='Logo', related='company_id.logo',
                         store=True)

    @api.constrains('date', 'date_retenu')
    def _check_dates(self):
        for record in self:
            if record.date and record.date_retenu and record.date > record.date_retenu:
                raise UserError(_("La date d'avance doit être inférieure ou égale à la date de retenue"))

    @api.onchange('date', 'date_retenu')
    def _onchange_dates(self):
        if self.date and self.date_retenu and self.date > self.date_retenu:
            return {
                'warning': {
                    'title': _("Avertissement"),
                    'message': _("La date d'avance doit être inférieure ou égale à la date de retenue")
                }
            }

    def action_print_report(self):
        self.ensure_one()
        if self.state != 'approve':
            raise UserError(_('Le rapport ne peut être imprimé que pour les avances approuvées'))

        return self.env.ref('nn_advance.action_report_salary_advance').report_action(self)


    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            # Récupérer le département de l'employé
            self.department = self.employee_id.department_id.id

            # Récupérer le contrat en cours
            current_contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open')  # Filtre sur les contrats actifs
            ], limit=1)

            # Affecter le contrat au champ employee_contract_id
            self.employee_contract_id = current_contract.id


    def cancel(self):
        self.state = 'cancel'
        # Notification pour l'employé
        if self.employee_id.user_id:
            self.message_post(
                body=_("Votre demande d'avance sur salaire a été annulée."),
                partner_ids=[self.employee_id.user_id.partner_id.id]
            )

    def reject(self):
        self.state = 'reject'
        # Notification pour l'employé
        if self.employee_id.user_id:
            self.message_post(
                body=_("Votre demande d'avance sur salaire a été rejetée."),
                partner_ids=[self.employee_id.user_id.partner_id.id]
            )

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals['name'] == 'Av/':
            vals['name'] = self.env['ir.sequence'].next_by_code('salary.advance.seq') or 'Av/'
        return super(SalaryAdvancePayment, self).create(vals)


    def approve_request(self):
        """This Approve the employee salary advance request."""
        current_month = datetime.strptime(str(self.date), '%Y-%m-%d').date().month

        if not self.employee_contract_id:
            raise UserError('Définir un contrat pour le salarié')

        # Get wage from contract directly without struct_id
        adv = self.advance
        amt = self.employee_contract_id.wage
        if adv > amt and not self.exceed_condition:
            raise UserError('Le montant de l\'avance est supérieur à celui alloué')

        if not self.advance:
            raise UserError('Vous devez saisir le montant de l\'avance sur salaire')

        payslip_obj = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id),
                                                     ('state', '=', 'done'), ('date_from', '<=', self.date_retenu),
                                                     ('date_to', '>=', self.date_retenu)])
        if payslip_obj:
            raise UserError("Le salaire de ce mois est déjà calculé")

        self.state = 'waiting_approval'
        # Notification pour le département comptable
        accountant_group = self.env.ref('account.group_account_manager', raise_if_not_found=False)
        if accountant_group:
            accountant_users = accountant_group.users
            partner_ids = accountant_users.mapped('partner_id').ids
            self.message_post(
                body=_(f"Une demande d'avance sur salaire pour {self.employee_id.name} "
                       f"nécessite une validation comptable. Montant: {self.advance} {self.currency_id.symbol}"),
                partner_ids=partner_ids
            )


    def approve_request_acc_dept(self):
        """This Approve the employee salary advance request from accounting department.
                   """
        if not self.advance:
            raise UserError('Vous devez saisir le montant de l\'avance sur salaire')

        self.state = 'approve'
        # Notification pour l'employé
        if self.employee_id.user_id:
            self.message_post(
                body=_("Votre demande d'avance sur salaire a été approuvée."),
                partner_ids=[self.employee_id.user_id.partner_id.id]
            )
        return True
