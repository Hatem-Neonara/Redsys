from odoo import models, fields, api


class CrmLeadPointEstimationProduct(models.Model):
    _name = 'crm.lead.estimation.product'
    _description = "Estimation de Produit Point CRM"

    lead_id = fields.Many2one('crm.lead', string="Opportunité", required=True, ondelete='cascade')

    # Currency field with Euro as default
    currency_id = fields.Many2one('res.currency', string="Devise")

    # Identifiants
    pn = fields.Char(related='product_id.barcode', string="PN", required=True)
    product_id = fields.Many2one('product.template', string="Produit", required=True)

    # Quantité & Prix en Euro
    quantity = fields.Integer(string="Quantité", required=True)
    prix_unitaire = fields.Float(string="PU(€)", required=True, digits=(12, 3))
    estimation_transport_devis = fields.Float(string="Transport(€)", digits=(12, 2))
    total_devis = fields.Float(string="Total(€)", compute="_compute_total_devis", store=True, digits=(12, 2))

    # Montants en Dinar (DT)
    total_dinar = fields.Float(string="Total(DT)", compute="_compute_total_dinar", store=True, digits=(12, 3))
    estimation_transport_dinar = fields.Float(string="Transport(DT)", compute="_compute_transport_dinar",
                                              store=True, digits=(12, 3))

    fee_dd = fields.Float(string="DD", compute='_compute_fee_dd', store=True, digits=(12, 3))
    taux_change = fields.Float(string="Taux de Change", related="currency_id.rate", store=True,
                               digits=(12, 3))
    taux_dd_id = fields.Many2one('taux.dd', string="Taux DD")

    transit = fields.Float(string="Transit", digits=(12, 3))
    cert = fields.Float(string="CERT", digits=(12, 3))

    prix_revient = fields.Float(string="Prix de Revient", compute='_compute_prix_revient', store=True, digits=(12, 3))
    margin_percentage = fields.Float(string="Pourcentage de marge", digits=(12, 3))
    margin = fields.Float(string="Marge", compute='_compute_margin', store=True, digits=(12, 3))
    prix_final = fields.Float(string="Prix Final (DT)", compute="_compute_prix_final", store=True, digits=(12, 3))
    price_unit = fields.Float(string="PU Conseillé ", compute='_compute_price_unit')


    # -------------------
    # Compute Functions
    # -------------------

    @api.depends('quantity', 'prix_unitaire')
    def _compute_total_devis(self):
        for rec in self:
            rec.total_devis = rec.quantity * rec.prix_unitaire

    @api.depends('total_devis', 'estimation_transport_devis', 'taux_change')
    def _compute_total_dinar(self):
        """Convert Euro amounts to Tunisian Dinar using dynamic rate"""
        for rec in self:
            rec.total_dinar = rec.total_devis * rec.taux_change

    @api.depends('total_dinar', 'taux_dd_id')
    def _compute_fee_dd(self):
        for rec in self:
            if rec.taux_dd_id and rec.taux_dd_id.name:
                rec.fee_dd = (rec.total_dinar + rec.estimation_transport_dinar) * (rec.taux_dd_id.name / 100)
            else:
                rec.fee_dd = 0.0

    @api.depends('total_dinar', 'fee_dd', 'transit', 'cert', 'estimation_transport_dinar')
    def _compute_prix_revient(self):
        for rec in self:
            rec.prix_revient = rec.total_dinar + rec.estimation_transport_dinar + rec.fee_dd + rec.transit + rec.cert

    @api.depends('estimation_transport_devis', 'taux_change')
    def _compute_transport_dinar(self):
        for rec in self:
            if rec.estimation_transport_devis and rec.taux_change:
                rec.estimation_transport_dinar = rec.estimation_transport_devis * rec.taux_change
            else:
                rec.estimation_transport_dinar = 0.0

    @api.depends('prix_revient', 'margin_percentage')
    def _compute_margin(self):
        for rec in self:
            if rec.prix_revient and rec.margin_percentage:
                rec.margin = rec.prix_revient * rec.margin_percentage
            else:
                rec.margin = 0.0

    @api.depends('prix_revient', 'margin')
    def _compute_prix_final(self):
        for rec in self:
            rec.prix_final = rec.prix_revient + rec.margin
    @api.depends('prix_final','quantity')
    def _compute_price_unit(self):
        for rec in self :
            if rec.quantity and rec.prix_final:
                rec.price_unit = rec.prix_final/ rec.quantity
            else:
                rec.price_unit = 0.0
