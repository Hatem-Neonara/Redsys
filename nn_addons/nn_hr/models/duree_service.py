from datetime import timedelta
from math import fabs

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    service_hire_date = fields.Date(
        string="Date d'Embauche",
        groups="hr.group_hr_user",
        tracking=True,
    )
    service_start_date = fields.Date(
        string="Date de Début",
        groups="hr.group_hr_user",
        tracking=True,
    )
    service_termination_date = fields.Date(
        string="Date Fin de Contrat",
        related="departure_date",
    )
    service_duration = fields.Integer(
        string="Durée du service",
        groups="hr.group_hr_user",
        readonly=True,
        compute="_compute_service_duration",
    )
    service_duration_years = fields.Integer(
        string="Durée du service (année)",
        groups="hr.group_hr_user",
        readonly=True,
        compute="_compute_service_duration_display",
    )
    service_duration_months = fields.Integer(
        string="Durée du service (mois)",
        groups="hr.group_hr_user",
        readonly=True,
        compute="_compute_service_duration_display",
    )
    service_duration_days = fields.Integer(
        string="Durée du service (jours)",
        groups="hr.group_hr_user",
        readonly=True,
        compute="_compute_service_duration_display",
    )

    @api.depends("service_start_date", "service_termination_date")
    def _compute_service_duration(self):
        for record in self:
            service_until = record.service_termination_date or fields.Date.today()
            if record.service_start_date and service_until > record.service_start_date:
                service_since = record.service_start_date
                service_duration = fabs(
                    (service_until - service_since) / timedelta(days=1)
                )
                record.service_duration = int(service_duration)
            else:
                record.service_duration = 0

    @api.depends("service_start_date", "service_termination_date")
    def _compute_service_duration_display(self):
        for record in self:
            service_until = record.service_termination_date or fields.Date.today()
            if record.service_start_date and service_until > record.service_start_date:
                service_duration = relativedelta(
                    service_until, record.service_start_date
                )
                record.service_duration_years = service_duration.years
                record.service_duration_months = service_duration.months
                record.service_duration_days = service_duration.days
            else:
                record.service_duration_years = 0
                record.service_duration_months = 0
                record.service_duration_days = 0

    @api.onchange("service_hire_date")
    def _onchange_service_hire_date(self):
        if not self.service_start_date:
            self.service_start_date = self.service_hire_date

    def _get_date_start_work(self):
        return self.sudo().service_start_date or super()._get_date_start_work()







