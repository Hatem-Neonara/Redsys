from odoo import models, fields


class SaleQuotation(models.Model):
    _inherit = 'sale.quotation'

    crm_lead_id = fields.Many2one(
        comodel_name='crm.lead',
        string="CRM Lead",
        ondelete='cascade'
    )

    def action_confirm(self):
        self.ensure_one()

        # 🔹 Create Sale Order based on Quotation
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'quotation_seq': self.name,
            'payment_term_id': self.payment_term_id.id,
            'pricelist_id': self.pricelist_id.id,
            'currency_id': self.currency_id.id,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            'order_line': [(0, 0, {
                'display_type': line.display_type,
                'product_id': line.product_id.id,
                'name': line.name,
                'product_uom_qty': line.product_uom_qty,
                'price_unit': line.price_unit,
                'discount': line.discount,
            }) for line in self.order_line],
        })

        # ✅ Mark this quotation as confirmed
        self.state = "sale"
        self.locked = True

        # 🔍 Update related RFQ if found
        rfq = self.env['purchase.rfq'].search([
            ('crm_lead_id', '=', self.crm_lead_id.id)
        ], limit=1)

        if rfq:
            rfq.sale_quotation_confirmed = True

        # 🎯 Open the newly created Sale Order
        return {
            'name': 'Sale Order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def get_portal_last_transaction(self):
        """Get the last transaction for this quotation"""
        # This should return a transaction object or a dummy object with a 'state' attribute
        # You'll need to implement this based on your business logic

        # Example implementation (adjust based on your needs):
        if hasattr(self, 'transaction_ids') and self.transaction_ids:
            return self.transaction_ids.sorted('create_date', reverse=True)[0]

        # Return a dummy object if no transactions exist
        class DummyTransaction:
            state = 'done'  # or whatever default state you want

        return DummyTransaction()


class SaleQuotationLine(models.Model):
    _inherit = 'sale.quotation.line'

    pn = fields.Char(
        string="PN",  # Part Number
        related='product_id.barcode',
        store=True,
        readonly=True
    )
