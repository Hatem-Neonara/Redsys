from odoo import fields, api, models, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class PurchaseOrderUpdated(models.Model):
    _inherit = 'purchase.order'

    crm_lead_id = fields.Many2one(
        'crm.lead',
        string="CRM Lead",
    )

class PurchaseOrderLineUpdated(models.Model):
    _inherit = 'purchase.order.line'

    barcode = fields.Char(string="PN", related='product_id.barcode')


class PurchaseRfqLineInherited(models.Model):
    _inherit = 'purchase.rfq.line'

    barcode = fields.Char(string="PN", related='product_id.barcode')
    price_unit = fields.Float(string='P.U.', required=True, digits='Product Price', readonly=False, store=True)
    currency_id = fields.Many2one('res.currency', string="Devise", related="order_id.currency_id")

class PurchaseRFQUpdatedWorkflow(models.Model):
    _inherit = 'purchase.rfq'

    currency_id = fields.Many2one('res.currency', string="Devise", readonly=False)

    crm_lead_id = fields.Many2one(
        'crm.lead',
        string="CRM Lead",
        help="Related CRM opportunity or lead"
    )

    def button_confirm(self):
        for rec in self:
            if not rec.suppliers_ids:
                raise UserError("Veuillez sélectionner au moins un fournisseur.")
        self.write({'state': 'rfq'})


    def button_creat_po(self):
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'crm_lead_id': self.crm_lead_id.id,
            'rfq_seq': self.name,
            'partner_ref': self.partner_ref,
            'payment_term_id': self.payment_term_id.id,
            'currency_id': self.currency_id.id,
            'order_line': [(0, 0, {
                'display_type': line.display_type,
                'product_id': line.product_id.id,
                'name': line.name,
                'product_qty': line.product_qty,
                'price_unit': line.price_unit,
            }) for line in self.order_line],
        })
        # Store the relation to the newly created PO
        self.write({
            'purchase_order_id': purchase_order.id,
            'state': "purchase"
        })
        return {
            'name': 'Purchase Order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_view_crm(self):
        self.ensure_one()
        crm_lead = self.env['crm.lead'].search([('purchase_rfq_ids', '=', self.id)], limit=1)
        return {
            'type': 'ir.actions.act_window',
            'name': 'CRM',
            'res_model': 'crm.lead',
            'res_id': crm_lead.id,
            'view_mode': 'form',
            'target': 'current',
        }

    crm_lead_exist = fields.Boolean(
        string='Crm Lead',
        compute='_compute_crm_lead_exist'
    )

    def _compute_crm_lead_exist(self):
        self.ensure_one()
        purchase_order = self.env['crm.lead'].search([('purchase_rfq_ids', '=', self.id)])
        if purchase_order:
            self.crm_lead_exist = True
        else:
            self.crm_lead_exist = False

    sale_quotation_confirmed = fields.Boolean(string="Devis confirmé", default=False)

    def action_confirm_sale(self):
        for rec in self:
            if not rec.sale_quotation_confirmed:
                for line in rec.order_line:
                    if line.price_unit <= 0:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'Prix Invalide',
                                'message': "Le prix unitaire ne peut pas être inférieur ou égal à zéro.",
                                'type': 'warning',  # options: success, warning, danger, info
                                'sticky': False,  # stays until clicked if True
                            }
                        }

                rec.sale_quotation_confirmed = True
