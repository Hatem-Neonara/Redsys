from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    """Inherits the AccountAnalytic model to add new budget line field that
    connect with the budget line modules"""
    _inherit = "account.analytic.account"

    budget_line = fields.One2many('budget.lines',
                                  'analytic_account_id',
                                  'Budget Lines')
