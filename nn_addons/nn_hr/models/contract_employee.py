# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrContractType(models.Model):
    _inherit = 'hr.contract.type'
    _description = 'Contract Type'

    active = fields.Boolean(default=True)
    term_ids = fields.One2many('hr.contract.type.term', 'contract_type_id')
    country_id = fields.Many2one('res.country', string="Country")



class HrContractTypeTerm(models.Model):
    _name = 'hr.contract.type.term'
    _description = 'Employee Contract Types Terms'

    contract_type_id = fields.Many2one('hr.contract.type')
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    body = fields.Text(required=True)


class HrContract(models.Model):
    _inherit = "hr.contract"

    contract_type_id = fields.Many2one("hr.contract.type", string="Type Contrat")

    code = fields.Char(string='Contract No', tracking=True, copy=False,
                       store=True, readonly=True, index=True,
                       default='Contract')

    # Sequence for employee
    @api.model
    def create(self, vals):
        if not vals.get('code') or vals['code'] == 'Contract':
            vals['code'] = self.env['ir.sequence'].next_by_code('hr.contract') or 'Contract'
        return super(HrContract, self).create(vals)
