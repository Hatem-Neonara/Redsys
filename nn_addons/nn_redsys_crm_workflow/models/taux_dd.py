# -*- coding: utf-8 -*-
from odoo import models, fields, api

class Toded1(models.Model):
    _name = 'taux.dd'
    _description = 'Taux DD'

    name = fields.Float(string='Taux')
    description = fields.Text(string='Description')
