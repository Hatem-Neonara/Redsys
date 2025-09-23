from odoo import models, fields, api
from datetime import datetime

class ProductTemplate(models.Model):
    _inherit = 'product.template'


    creation_date = fields.Date(string="Date de création", readonly=True)
    last_movement_date = fields.Datetime(string="Date du dernier mouvement", compute="_compute_last_movement_date", store=True)

    main_supplier_id = fields.Many2one('res.partner', string="Fournisseur Principal")

    arrival_date = fields.Date(string="Date d’arrivée")
    departure_date = fields.Date(string="Date de sortie")
    supplier_name = fields.Char(string="Nom du fournisseur")
    invoice_reference = fields.Char(string="Référence de la facture")

    purchase_rfq_id = fields.Many2one('purchase.order', string='Dernier RFQ', compute='_compute_purchase_rfq', store=True)


    @api.depends('qty_available')
    def _compute_last_movement_date(self):
        for product in self:
            movements = self.env['stock.move'].search([
                ('product_id.product_tmpl_id', '=', product.id)
            ], order="date desc", limit=1)
            product.last_movement_date = movements.date if movements else False

    @api.depends('qty_available')
    def _compute_purchase_rfq(self):
        for rec in self:
            latest_line = self.env['purchase.order.line'].search([
                ('product_id.product_tmpl_id', '=', rec.id)
            ], order="create_date desc", limit=1)
            rec.purchase_rfq_id = latest_line.order_id if latest_line else False

class ProductProduct(models.Model):
    _inherit = 'product.product'


    creation_date = fields.Date(
        related='product_tmpl_id.creation_date',
        string="Date de création",
        store=True,
        readonly=False
    )
    last_movement_date = fields.Datetime(
        related='product_tmpl_id.last_movement_date',
        string="Date du dernier mouvement",
        store=True,
        readonly=False
    )
    main_supplier_id = fields.Many2one(
        related='product_tmpl_id.main_supplier_id',
        string="Fournisseur Principal",
        store=True,
        readonly=False
    )
    arrival_date = fields.Date(
        related='product_tmpl_id.arrival_date',
        string="Date d’arrivée",
        store=True,
        readonly=False
    )
    departure_date = fields.Date(
        related='product_tmpl_id.departure_date',
        string="Date de sortie",
        store=True,
        readonly=False
    )
    supplier_name = fields.Char(
        related='product_tmpl_id.supplier_name',
        string="Nom du fournisseur",
        store=True,
        readonly=False
    )
    invoice_reference = fields.Char(
        related='product_tmpl_id.invoice_reference',
        string="Référence de la facture",
        store=True,
        readonly=False
    )
    purchase_rfq_id = fields.Many2one(
        related='product_tmpl_id.purchase_rfq_id',
        string='Dernier RFQ',
        store=True,
        readonly=False
    )

    @api.model
    def _check_critical_stock(self):
        critical_products = self.search([('qty_available', '<=', 1)])
        for product in critical_products:
            product.message_post(
                body=f"<b>Alerte:</b> Le stock de l’article '{product.display_name}' est critique (≤ 1)."
            )