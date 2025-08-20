from odoo import fields, api, models


class InitialProductList(models.Model):
    _name = 'crm.initial.product.list'
    _description = 'Initial Product List'

    description = fields.Text(string="Description",related='product_id.description_sale', store = True,readonly=False)
    product_id = fields.Many2one('product.template', string="Article")
    barcode = fields.Char(string="PN",readonly=False)
    name = fields.Char(string="Nom Article")
    quantity = fields.Float(string="Quantité", default=1.0)
    unit_of_measure_id = fields.Many2one(
        comodel_name='uom.uom',
        string="UdM",
        ondelete='restrict'  # Better than cascade for UoM
    )
    lead_id = fields.Many2one(
        comodel_name='crm.lead',
        string="CRM Lead",
        ondelete='cascade'
    )
    detailed_type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product')
    ], string='Type Article', default='product', required=True,
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
             'A consumable product is a product for which stock is not managed.\n'
             'A service is a non-material product you provide.')

    taux_tva = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        domain="[('type_tax_use', '=', 'sale')]",
        help="Taxes that apply on the product sale"
    )

    @api.model
    def default_get(self, fields_list):
        """Set default Unit of Measure to prevent '_unknown' object errors"""
        res = super(InitialProductList, self).default_get(fields_list)
        if 'unit_of_measure_id' in fields_list and not res.get('unit_of_measure_id'):
            # Get reference to default UoM (usually 'Unit(s)')
            default_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
            if default_uom:
                res['unit_of_measure_id'] = default_uom.id
        return res

