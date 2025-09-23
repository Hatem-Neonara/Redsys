from datetime import datetime, date, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DocumentType(models.Model):
    _name = 'document.type'
    _description = 'Document Type'

    name = fields.Char(string="Type Document", required=True, help="Document Type Name")


class HrEmployeeDocument(models.Model):
    _name = 'hr.employee.document'
    _description = 'HR Employee Documents'
    _check_company_auto = True

    def mail_reminder(self):
        """Sending document expiry notification to employees."""

        now = datetime.now() + timedelta(days=1)
        # date_now = now.date()
        date_now = fields.Date.today()
        match = self.search([])
        for i in match:
            if i.expiry_date:
                if i.notification_type == 'single':
                    exp_date = fields.Date.from_string(i.expiry_date)
                    print('exp_date :', exp_date)
                    # if date_now == exp_date:
                    if date_now == i.expiry_date:
                        mail_content = "  Bonjour  " + i.employee_ref.name + ",<br>Le Document " + i.name + " Expire le " + \
                                       str(i.expiry_date) + ". Merci de prendre les mesures nécessaires"
                        main_content = {
                            'subject': _('Document-%s Expire le %s') % (i.name, i.expiry_date),
                            'author_id': self.env.user.partner_id.id,
                            'body_html': mail_content,
                            'email_to': i.manager_ref.work_email,
                        }
                        self.env['mail.mail'].create(main_content).send()
                elif i.notification_type == 'multi':
                    exp_date = fields.Date.from_string(i.expiry_date) - timedelta(days=i.before_days)
                    if date_now == exp_date or date_now == i.expiry_date:  # on Expire date and few days(As it set) before expire date
                        print('mail send started before few')
                        mail_content = "  Bonjour  " + i.manager_ref.name + ",<br>Le Document " + i.name + \
                                       "relatif à l'employé" + i.employee_ref.name + \
                                       " Expire le " + str(i.expiry_date) + \
                                       ". Merci de prendre les mesures nécessaires"
                        main_content = {
                            'subject': _('Document-%s Expire le %s') % (i.name, i.expiry_date),
                            'author_id': self.env.user.partner_id.id,
                            'body_html': mail_content,
                            'email_to': i.manager_ref.work_email,
                        }
                        self.env['mail.mail'].create(main_content).send()
                elif i.notification_type == 'everyday':
                    exp_date = fields.Date.from_string(i.expiry_date) - timedelta(days=i.before_days)
                    # if date_now >= exp_date and date_now == i.expiry_date:
                    if date_now >= exp_date or date_now == i.expiry_date:
                        print('Everyday till START sending')

                        mail_content = "  Bonjour  " + i.manager_ref.name + ",<br>Le Document " + i.name + \
                                       "relatif à l'employé" + i.employee_ref.name + \
                                       " Expire le " + str(i.expiry_date) + \
                                       ". Merci de prendre les mesures nécessaires"
                        main_content = {
                            'subject': _('Document-%s Expire le %s') % (i.name, i.expiry_date),
                            'author_id': self.env.user.partner_id.id,
                            'body_html': mail_content,
                            'email_to': i.manager_ref.work_email,
                        }
                        self.env['mail.mail'].create(main_content).send()
                elif i.notification_type == 'everyday_after':
                    exp_date = fields.Date.from_string(i.expiry_date) + timedelta(days=i.before_days)
                    # if date_now == exp_date and date_now == i.expiry_date:
                    if date_now <= exp_date or date_now == i.expiry_date:
                        print('Every day after START sending')
                        mail_content = "  Bonjour  " + i.manager_ref.name + ",<br>Le Document " + i.name + \
                                       "relatif à l'employé" + i.employee_ref.name + \
                                       " Expire le " + str(i.expiry_date) + \
                                       ". Merci de prendre les mesures nécessaires"
                        main_content = {
                            'subject': _('Document-%s Expire le %s') % (i.name, i.expiry_date),
                            'author_id': self.env.user.partner_id.id,
                            'body_html': mail_content,
                            'email_to': i.manager_ref.work_email,
                        }
                        self.env['mail.mail'].create(main_content).send()
                else:
                    exp_date = fields.Date.from_string(i.expiry_date) - timedelta(days=7)
                    # if date_now >= exp_date:
                    if date_now == exp_date:
                        mail_content = "  Bonjour  " + i.manager_ref.name + ",<br>Le Document " + i.name + \
                                       "relatif à l'employé" + i.employee_ref.name + \
                                       " Expire le " + str(i.expiry_date) + \
                                       ". Merci de prendre les mesures nécessaires"
                        main_content = {
                            'subject': _('Document-%s Expire le %s') % (i.name, i.expiry_date),
                            'author_id': self.env.user.partner_id.id,
                            'body_html': mail_content,
                            'email_to': i.manager_ref.work_email,
                        }
                        self.env['mail.mail'].create(main_content).send()

    @api.constrains('expiry_date')
    def check_expr_date(self):
        for each in self:
            if each.expiry_date:
                exp_date = fields.Date.from_string(each.expiry_date)
                if exp_date < date.today():
                    raise Warning('Le document a expiré.')

    name = fields.Char(string='N° Document', required=True, copy=False, help='You can give your'
                                                                             'Document number.')
    company_id = fields.Many2one(comodel_name='res.company', related="employee_ref.company_id")
    description = fields.Text(string='Description', copy=False, help="Description")
    expiry_date = fields.Date(string='Date d\'Expiration', copy=False, help="Date d'expiration")
    employee_ref = fields.Many2one('hr.employee', invisible=0, copy=False)
    manager_ref = fields.Many2one('hr.employee', required=True, copy=False)
    doc_attachment_id = fields.Many2many('ir.attachment', 'doc_attach_rel', 'doc_id', 'attach_id3',
                                         string="Pièce Jointe",
                                         copy=False)
    issue_date = fields.Date(string='Date d\'Emission', default=fields.datetime.now(), copy=False)
    document_type = fields.Many2one('document.type', string="Type Document")
    before_days = fields.Integer(string="Jours", help="Combien de jours avant de recevoir l'e-mail de notification")
    notification_type = fields.Selection([
        ('single', 'Notification à la date d\'expiration'),
        ('multi', 'Notification avant quelques jours'),
        ('everyday', 'Tous les jours jusqu\'à la date d\'expiration'),
        ('everyday_after', 'Notification à et après l\'expiration')
    ], string='Type de Notification',
        help="""
       Notification à la date d'expiration: vous recevrez une notification uniquement à la date d'expiration.
         Notification avant quelques jours : Vous recevrez une notification dans 2 jours. À la date d'expiration et au nombre de jours avant la date.
         Tous les jours jusqu'à la date d'expiration: vous recevrez une notification à partir du nombre de jours jusqu'à la date d'expiration du document.
         Notification à l'expiration et après: vous recevrez une notification à la date d'expiration et continue jusqu'à jours.
         Si vous n'en avez pas sélectionné, vous recevrez une notification dans les 7 jours suivant l'expiration du document.""")


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _document_count(self):
        for each in self:
            document_ids = self.env['hr.employee.document'].sudo().search([('employee_ref', '=', each.id)])
            each.document_count = len(document_ids)

    def document_view(self):
        self.ensure_one()
        domain = [
            ('employee_ref', '=', self.id)]
        return {
            'name': _('Documents'),
            'domain': domain,
            'res_model': 'hr.employee.document',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Cliquez pour créer pour les nouveaux documents
                        </p>'''),
            'limit': 80,
            'context': "{'default_employee_ref': %s}" % self.id
        }

    document_count = fields.Integer(compute='_document_count', string='# Documents')


class HrEmployeeAttachment(models.Model):
    _inherit = 'ir.attachment'

    doc_attach_rel = fields.Many2many('hr.employee.document', 'doc_attachment_id', 'attach_id3', 'doc_id',
                                      string="Pièce Jointe", invisible=1)
    attach_rel = fields.Many2many('hr.document', 'attach_id', 'attachment_id3', 'document_id',
                                  string="Pièce Jointe", invisible=1)


class HrDocument(models.Model):
    _name = 'hr.document'
    _description = 'Documents Template'
    _check_company_auto = True

    name = fields.Char(string='Document', required=True, copy=False)
    note = fields.Text(string='Note', copy=False, help="Note")
    attach_id = fields.Many2many('ir.attachment', 'attach_rel', 'doc_id', 'attach_id3', string="Pièce Jointe",
                                 help='You can attach the copy of your document', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', required=True, index=True,
                                 default=lambda self: self.env.company)
