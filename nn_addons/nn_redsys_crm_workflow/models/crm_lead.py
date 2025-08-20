from odoo import fields,api , models
from odoo.exceptions import UserError, ValidationError
from wheel.macosx_libfile import FAT_MAGIC

class CrmUpdatedWorkflow(models.Model):
    _inherit = 'crm.lead'

    # New Added fields and functions
    initial_product_list_ids = fields.One2many(
        comodel_name='crm.initial.product.list',
        inverse_name='lead_id',
        string='Initial Product List'
    )
    final_product_list_generated = fields.Boolean(string="Final Product is generated" , readonly=False,default= False)

    final_product_list_ids = fields.One2many(
    comodel_name='crm.final.product.list',
    inverse_name='lead_id',
    string="Final Product Lines"
    )

    # Helper function to handle the notification display and page reload
    def notify_product_status(self, product_found):
        if product_found:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'next': {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
                    'title': "Success",
                    'message': "The product already exists.",
                    'type': 'success',
                    'sticky': False,
                }}  # Use 'next' to trigger reload
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'next': {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
                    'title': "Success",
                    'message': "A new product has been created.",
                    'type': 'success',
                    'sticky': False,
                }}  # Use 'next' to trigger reload
            }
    # Main function to generate final product lines
    def action_generate_final_product_lines(self):
        for lead in self:
            final_lines = []
            product_found = False  # Flag to track if any product is found

            for line in lead.initial_product_list_ids:
                barcode = line.barcode
                product = None
                line_product_found = False  # Track if this specific line's product exists

                # Scenario 1: Line has barcode - search for existing product
                if barcode:
                    product = self.env['product.template'].search([('barcode', '=', barcode)], limit=1)

                    if product:
                        # Existing product found - use it
                        final_lines.append((0, 0, {
                            'barcode': barcode,
                            'product_id': product.id,
                            'description': line.description,
                            'quantity': line.quantity,
                            'uom_id': product.uom_id.id,
                            'price_unit': product.list_price,
                        }))
                        line_product_found = True
                    else:
                        # No existing product with this barcode - create new one
                        new_product = self.env['product.template'].create({
                            'name': line.name or f'New Product {barcode}',
                            'barcode': barcode,
                            'uom_id': line.unit_of_measure_id.id,
                            'taxes_id': [(6, 0, line.taux_tva.ids)] if line.taux_tva else False,
                            'uom_po_id': line.unit_of_measure_id.id,
                            'type': line.detailed_type,
                            'detailed_type': line.detailed_type,
                            'list_price': 0.0,
                            'description_purchase': line.description,
                        })

                        final_lines.append((0, 0, {
                            'barcode': barcode,
                            'product_id': new_product.id,
                            'description': line.description,
                            'quantity': line.quantity,
                            'uom_id': new_product.uom_id.id,
                            'price_unit': new_product.list_price,
                        }))

                # Scenario 2: Line has no barcode - always create new product
                else:
                    final_lines.append((0, 0, {
                        'barcode': '',  # ou barcode vide
                        'product_id': line.product_id.id,
                        'description': line.description,
                        'quantity': line.quantity,
                        'uom_id': line.unit_of_measure_id.id,
                    }))
                    product_found = True



            # Update the final product list
            lead.final_product_list_ids = [(5, 0, 0)] + final_lines
            lead.final_product_list_generated = True

            # Call the notification function with appropriate message

        return None

    def action_create_rfq(self):
        self.ensure_one()

        if not self.id:
            raise UserError("Vous devez enregistrer l'enregistrement avant de créer le RFQ.")

        if not self.final_product_list_ids or not self.final_product_list_generated:
            raise UserError("Aucune liste de produits finaux n’a été générée.")


        # 🔍 Filtrer les lignes avec produits physiques uniquement (exclut tous les services)
        valid_lines = self.final_product_list_ids.filtered(
            lambda line: line.product_id and line.product_id.detailed_type != 'service'
        )

        if not valid_lines:
            raise UserError("Aucun produit physique à ajouter au RFQ (tous les produits sont de type 'service').")

        # 🧾 Créer le RFQ
        purchase_rfq_vals = {
            'partner_id': self.partner_id.id,
            'crm_lead_id': self.id,
        }
        purchase_rfq = self.env['purchase.rfq'].sudo().create(purchase_rfq_vals)

        for rfq_line in valid_lines:
            self.env['purchase.rfq.line'].sudo().create({
                'order_id': purchase_rfq.id,
                'product_id': rfq_line.product_id.product_variant_id.id,
                'barcode': rfq_line.barcode,
                'name': rfq_line.product_id.name,
                'product_qty': rfq_line.quantity,
                'product_uom': rfq_line.uom_id.id,
                'price_unit': 0,
            })

        self.rfq_created = True

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.rfq',
            'view_mode': 'form',
            'res_id': purchase_rfq.id,
            'target': 'current',
        }

    purchase_rfq_ids = fields.One2many(
        'purchase.rfq',
        'crm_lead_id',
        string="Purchase Orders"
    )
    order_line = fields.One2many(related='purchase_rfq_ids.order_line', string='RFQ Lines', copy=True)
    purchase_order_ids = fields.One2many(
        'purchase.order',
        'crm_lead_id',
        string="Purchase Orders"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id.id,
        store=True,
    )

    purchase_order_created = fields.Boolean(
        string='Nombre de Commandes',
        compute='_compute_purchase_order_created'
    )
    def _compute_purchase_order_created(self):
        self.ensure_one()
        purchase_order = self.env['purchase.order'].search([('crm_lead_id','=',self.id)])
        if purchase_order:
            self.purchase_order_created = True
        else:
            self.purchase_order_created = False


    def action_view_purchase_rfq(self):
        self.ensure_one()
        purchase_order = self.env['purchase.order'].search([('crm_lead_id','=',self.id)],limit=1)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order',
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    rfq_created = fields.Boolean(
        string="Nombre de RFQ",default = False
    )

    def action_view_rfqs(self):
        self.ensure_one()
        rfq = self.env['purchase.rfq'].search([('crm_lead_id', '=', self.id)], limit=1)
        if rfq:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Demande de prix',
                'res_model': 'purchase.rfq',
                'res_id': rfq.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # Optional: show warning if no RFQ found
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Aucun RFQ',
                    'message': 'Aucune demande de prix liée à cette opportunité.',
                    'type': 'warning',
                }
            }


    estimation_product_ids = fields.One2many('crm.lead.estimation.product', 'lead_id',
                                             string="Liste des Estimations Produits",
                                             compute='_compute_estimation_products',
                                             readonly=False, store=True)
    @api.depends('purchase_rfq_ids','purchase_rfq_ids.order_line')
    def _compute_estimation_products(self):

        for rec in self:
            values = []
            for line in rec.purchase_rfq_ids:
                for order_line in line.order_line:
                    values.append((0,0,{
                        'product_id':order_line.product_id.product_tmpl_id.id,
                        'prix_unitaire':order_line.price_unit,
                        'quantity':order_line.product_qty,
                        'currency_id':order_line.currency_id.id,
                    }))
                rec.estimation_product_ids= [(5,0,0)] + values

    @api.onchange('estimation_product_ids')
    def _onchange_sync_prices(self):
        print("🟡 estimation_product_ids changed, syncing prices...")

        estimation_map = {
            est.product_id.id: est.price_unit
            for est in self.estimation_product_ids
            if est.product_id and est.price_unit
        }

        print("🔄 Syncing prices from estimation to final product list...")

        for final in self.final_product_list_ids:
            if final.product_id and final.product_id.id in estimation_map:
                print(
                    f"➡ Updating {final.product_id.name}: {final.price_unit} -> {estimation_map[final.product_id.id]}"
                )
                final.price_unit = estimation_map[final.product_id.id]
    sale_quotation_created= fields.Boolean(string="Sale quotations created" ,default=False)
    def action_create_quotation(self):
        print("Y")
        self.ensure_one()

        if not self.id:
            raise UserError("Vous devez enregistrer l'enregistrement avant de créer le devis.")

        if not self.final_product_list_ids or not self.final_product_list_generated:
            raise UserError("Aucune liste de produits finaux n’a été générée.")
        if not self.partner_id:
            raise UserError("Veuillez sélectionner un client d'abord.")

        # 🧾 Créer le devis
        quotation_vals = {
            'partner_id': self.partner_id.id,
            'opportunity_id': self.id,
            'company_id': self.company_id.id or self.env.company.id,
            'crm_lead_id':self.id,
        }
        quotation = self.env['sale.quotation'].sudo().create(quotation_vals)

        for line in self.final_product_list_ids:
            self.env['sale.quotation.line'].sudo().create({
                'order_id': quotation.id,
                'product_id': line.product_id.product_variant_id.id,
                'name': line.description or line.product_id.name,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id if line.product_id.uom_id else False,
                'price_unit': line.price_unit or 0.0,
            })
        self.sale_quotation_created = True
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.quotation',
            'view_mode': 'form',
            'res_id': quotation.id,
            'target': 'current',
        }