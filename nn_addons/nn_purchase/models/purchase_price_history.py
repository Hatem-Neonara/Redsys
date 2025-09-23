from odoo import models, fields, api, _
from odoo.exceptions import UserError


class resConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_order_line_record_limit = fields.Integer(string="Record Limit", default=30,
                                                      config_parameter='purchase_order_line_record_limit')
    purchase_order_status = fields.Selection(
        [('purchase', 'Purchase order'), ('done', 'Done'), ('both', 'Both')], string="Price History Based On",
        default="purchase", config_parameter='purchase_order_status')

    def get_values(self):
        res = super(resConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        purchase_order_line_record_limit = ICPSudo.get_param('purchase_order_line_record_limit')
        purchase_order_status = ICPSudo.get_param('purchase_order_status')
        res.update(
            purchase_order_line_record_limit=int(purchase_order_line_record_limit),
            purchase_order_status=purchase_order_status
        )
        return res


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    order_partner_id = fields.Many2one('res.partner', string="Supplier",)

    def action_purchase_product_prices(self):
        """On clicking this button Purchase details such as partner and price
        could  be viewed """
        rel_view_id = self.env.ref('nn_purchase.purchase_order_line_view_tree')
        if self.order_partner_id.id:
            purchase_lines = self.env['purchase.order.line'].search(
                [('product_id', '=', self.id),
                 ('partner_id', '=', self.order_partner_id.id)],
                order='create_date DESC').mapped('id')
        else:
            purchase_lines = self.env['purchase.order.line'].search(
                [('product_id', '=', self.id)],
                order='create_date DESC').mapped('id')
        if not purchase_lines:
            raise UserError("No purchase history found.!")
        return {
            'domain': [('id', 'in', purchase_lines)],
            'views': [(rel_view_id.id, 'tree')],
            'name': 'Purchase History',
            'res_model': 'purchase.order.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

    def _get_purchase_price_history(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        purchase_history_obj = self.env['purchase.price.history'].sudo()
        purchase_history_ids = []
        domain = [('product_id', 'in', self.product_variant_ids.ids)]
        purchase_order_line_record_limit = int(ICPSudo.get_param('purchase_order_line_record_limit'))
        purchase_order_status = ICPSudo.get_param('purchase_order_status')
        if not purchase_order_line_record_limit:
            purchase_order_line_record_limit = 30
        if not purchase_order_status:
            purchase_order_status = 'purchase'
        if purchase_order_status == 'purchase':
            domain += [('state', '=', 'purchase')]
        elif purchase_order_status == 'done':
            domain += [('state', '=', 'done')]
        else:
            domain += [('state', '=', ('purchase', 'done'))]

        purchase_order_line_ids = self.env['purchase.order.line'].sudo().search(domain,
                                                                                limit=purchase_order_line_record_limit,
                                                                                order='create_date desc')
        for line in purchase_order_line_ids:
            purchase_price_history_id = purchase_history_obj.create({
                'name': line.id,
                'partner_id': line.partner_id.id,
                'user_id': line.order_id.user_id.id,
                'product_tmpl_id': line.product_id.product_tmpl_id.id,
                'variant_id': line.product_id.id,
                'purchase_order_id': line.order_id.id,
                'purchase_order_date': line.order_id.date_order,
                'product_uom_qty': line.product_qty,
                'unit_price': line.price_unit,
                'currency_id': line.currency_id.id,
                'total_price': line.price_total
            })
            purchase_history_ids.append(purchase_price_history_id.id)
        self.purchase_price_history_ids = purchase_history_ids

    purchase_price_history_ids = fields.Many2many("purchase.price.history", string="Purchase Price History",
                                                  compute="_get_purchase_price_history", store=True)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    order_partner_id = fields.Many2one('res.partner', string="Supplier", )

    def action_purchase_product_prices(self):
        """On clicking this button Purchase details such as partner and price
        could  be viewed """
        rel_view_id = self.env.ref('nn_purchase.purchase_order_line_view_price_history_tree')
        if self.order_partner_id.id:
            purchase_lines = self.env['purchase.order.line'].search(
                [('product_id', '=', self.id),
                 ('partner_id', '=', self.order_partner_id.id)],
                order='create_date DESC').mapped('id')
        else:
            purchase_lines = self.env['purchase.order.line'].search(
                [('product_id', '=', self.id)],
                order='create_date DESC').mapped('id')
        if not purchase_lines:
            raise UserError("No purchase history found.!")
        return {
            'domain': [('id', 'in', purchase_lines)],
            'views': [(rel_view_id.id, 'tree')],
            'name': 'Purchase History',
            'res_model': 'purchase.order.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

    def _get_purchase_price_history(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        purchase_history_obj = self.env['purchase.price.history'].sudo()
        purchase_history_ids = []
        domain = [('product_id', 'in', self.product_variant_ids.ids)]
        purchase_order_line_record_limit = int(ICPSudo.get_param('purchase_order_line_record_limit'))
        purchase_order_status = ICPSudo.get_param('purchase_order_status')
        if not purchase_order_line_record_limit:
            purchase_order_line_record_limit = 30
        if not purchase_order_status:
            purchase_order_status = 'purchase'
        if purchase_order_status == 'purchase':
            domain += [('state', '=', 'purchase')]
        elif purchase_order_status == 'done':
            domain += [('state', '=', 'done')]
        else:
            domain += [('state', '=', ('purchase', 'done'))]

        purchase_order_line_ids = self.env['purchase.order.line'].sudo().search(domain,
                                                                                limit=purchase_order_line_record_limit,
                                                                                order='create_date desc')
        for line in purchase_order_line_ids:
            purchase_price_history_id = purchase_history_obj.create({
                'name': line.id,
                'partner_id': line.partner_id.id,
                'user_id': line.order_id.user_id.id,
                'product_tmpl_id': line.product_id.product_tmpl_id.id,
                'variant_id': line.product_id.id,
                'purchase_order_id': line.order_id.id,
                'purchase_order_date': line.order_id.date_order,
                'product_uom_qty': line.product_qty,
                'unit_price': line.price_unit,
                'currency_id': line.currency_id.id,
                'total_price': line.price_total
            })
            purchase_history_ids.append(purchase_price_history_id.id)
        self.purchase_price_history_ids = purchase_history_ids

    purchase_price_history_ids = fields.Many2many("purchase.price.history", string="Purchase Price History",
                                                  compute="_get_purchase_price_history", store=True)

class PurchasePriceHistory(models.Model):
    _name = 'purchase.price.history'
    _description = 'Purchase Price History'

    name = fields.Many2one("purchase.order.line",string="Purchase Order Line")
    partner_id = fields.Many2one("res.partner",string="Customer")
    user_id = fields.Many2one("res.users",string="Sales Person")
    product_tmpl_id = fields.Many2one("product.template",string="Template")
    variant_id = fields.Many2one("product.product",string="Product")
    purchase_order_id = fields.Many2one("purchase.order",string="Purchase Order")
    purchase_order_date = fields.Datetime(string="Purchase Order Date")
    product_uom_qty = fields.Float(string="Quantity")
    unit_price = fields.Float(string="Price")
    currency_id = fields.Many2one("res.currency",string="Currency")
    total_price = fields.Monetary(string="Total")

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    purchase_date = fields.Datetime(string='Purchase Date', store=True,
                                    related='order_id.date_order',
                                    help='Purchase order date')

    def action_get_product_form(self):
        """This function is to view product form in purchase order line"""
        self.product_id.order_partner_id = self.order_id.partner_id.id
        return {
            'name': self.product_id.name,
            'view_mode': 'form',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': self.product_id.id
        }
