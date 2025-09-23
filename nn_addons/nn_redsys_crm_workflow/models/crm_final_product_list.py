from odoo import models, fields,api

class FinalProductList(models.Model):
    _name = 'crm.final.product.list'
    _description = 'Final Product List'

    barcode = fields.Char(string="PN", related='product_id.barcode',help="Part Number" ,readonly=False, store=True)
    product_id = fields.Many2one(
        comodel_name='product.template',
        string="Article"
    )
    description = fields.Text(string="Description",readonly=False ,store= True)
    quantity = fields.Float(string="Quantité", default=1.0)
    uom_id = fields.Many2one(
        related='product_id.uom_po_id',
        string="UdM",
        ondelete='restrict', readonly=False
    )
    price_unit = fields.Float(string="Prix Unitaire", related="product_id.list_price", readonly=False)
    lead_id = fields.Many2one(
        comodel_name='crm.lead',
        string="CRM Lead",
        ondelete='cascade'
    )
    prix_revient = fields.Float(
        string="Prix de Revient", store=True
    )
    detailed_type = fields.Selection(
        related='product_id.detailed_type',
        string="Type Article",
        store=True
    )
    rfq_service = fields.Boolean(string="RFQ service", default=False)
    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.detailed_type == 'service':
                rec.price_unit = rec.product_id.standard_price

