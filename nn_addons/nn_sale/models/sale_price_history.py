from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    order_partner_id = fields.Many2one('res.partner', string="Customer", )

    def action_sale_product_prices(self):
        """On clicking this button sales details such as partner and price could
         be viewed """
        rel_view_id = self.env.ref('nn_sale.sale_order_line_view_price_history_tree')
        if self.order_partner_id.id:
            sale_lines = self.env['sale.order.line'].search(
                [('product_id', '=', self.id),
                 ('order_partner_id', '=', self.order_partner_id.id)],
                order='create_date DESC').mapped('id')
        else:
            sale_lines = self.env['sale.order.line'].search(
                [('product_id', '=', self.id)],
                order='create_date DESC').mapped('id')
        if not sale_lines:
            raise UserError("No sales history found.!")
        return {
            'domain': [('id', 'in', sale_lines)],
            'views': [(rel_view_id.id, 'tree')],
            'name': 'Sales History',
            'res_model': 'sale.order.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sale_date = fields.Datetime(string='Sale Date', help='Sale Order date',
                                related='order_id.date_order', store=True)


