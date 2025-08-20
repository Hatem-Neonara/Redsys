# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone

from markupsafe import escape, Markup
from werkzeug.urls import url_encode

from odoo import api, Command, fields, models, _, SUPERUSER_ID
from odoo.osv import expression
from odoo.tools import format_amount, format_date, formatLang, groupby
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import UserError, ValidationError


class PurchaseRfq(models.Model):
    _name = "purchase.rfq"
    _inherit = ['portal.mixin', 'product.catalog.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Purchase RFQ"
    _rec_names_search = ['name', 'partner_ref']
    _order = 'priority desc, id desc'

    name = fields.Char('RFQ Reference', required=True, index='trigram', copy=False, default='New')
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], 'Priority', default='0', index=True)
    origin = fields.Char('Source Document', copy=False,
                         help="Reference of the document that generated this purchase order "
                              "request (e.g. a sales order)")
    partner_ref = fields.Char('Vendor Reference', copy=False, )
    date_order = fields.Date('Date RFQ', required=True, index=True, copy=False,
                             default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', string='Vendor', change_default=True, tracking=True,
                                 check_company=True, domain=[('is_supplier', '=', True)],
                                 help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'RFQ Sent'),
        ('rfq', 'RFQ'),
        ('purchase', 'Request PO'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    order_line = fields.One2many('purchase.rfq.line', 'order_id', string='RFQ Lines', copy=True)
    notes = fields.Html('Terms and Conditions')
    date_planned = fields.Date(
        string='Expected Arrival', index=True, copy=False, compute='_compute_date_planned', store=True, readonly=False,
        help="Delivery date promised by vendor. This date is used to determine expected arrival of products.")
    date_calendar_start = fields.Datetime(compute='_compute_date_calendar_start', readonly=True, store=True)

    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
                                         domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    tax_country_id = fields.Many2one(
        comodel_name='res.country',
        compute='_compute_tax_country_id',
        # Avoid access error on fiscal position, when reading a purchase order with company != user.company_ids
        compute_sudo=True,
        help="Technical field to filter the available taxes depending on the fiscal country and fiscal position.")
    tax_calculation_rounding_method = fields.Selection(
        related='company_id.tax_calculation_rounding_method',
        string='Tax calculation rounding method', readonly=True)
    payment_term_id = fields.Many2one('account.payment.term', 'Payment Terms',
                                      domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    incoterm_id = fields.Many2one('account.incoterms', 'Incoterm',
                                  help="International Commercial Terms are a series of predefined commercial terms used in international transactions.")

    product_id = fields.Many2one('product.product', related='order_line.product_id', string='Product')
    user_id = fields.Many2one(
        'res.users', string='Buyer', index=True, tracking=True,
        default=lambda self: self.env.user, check_company=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company.id)
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', string="Country code")

    mail_reminder_confirmed = fields.Boolean("Reminder Confirmed", default=False, readonly=True, copy=False,
                                             help="True if the reminder email is confirmed by the vendor.")
    mail_reception_confirmed = fields.Boolean("Reception Confirmed", default=False, readonly=True, copy=False,
                                              help="True if PO reception is confirmed by the vendor.")

    receipt_reminder_email = fields.Boolean('Receipt Reminder Email', compute='_compute_receipt_reminder_email')
    reminder_date_before_receipt = fields.Integer('Days Before Receipt', compute='_compute_receipt_reminder_email')

    purchase_order_id = fields.Many2one('purchase.order', string='Related Purchase Order',
                                        readonly=True, copy=False)
    purchase_order_count = fields.Integer(string='Purchase Order Count', compute='_compute_po_count')
    logo = fields.Binary(string='Logo', related='company_id.logo',
                         store=True)

    # company_id = fields.Many2one('res.company', string='Company',
    #                              default=lambda self: self.env.company)

    def _compute_po_count(self):
        for rfq in self:
            rfq.purchase_order_count = 1 if rfq.purchase_order_id else 0

    @api.constrains('company_id', 'order_line')
    def _check_order_line_company_id(self):
        for order in self:
            invalid_companies = order.order_line.product_id.company_id.filtered(
                lambda c: order.company_id not in c._accessible_branches()
            )
            if invalid_companies:
                bad_products = order.order_line.product_id.filtered(
                    lambda p: p.company_id and p.company_id in invalid_companies
                )
                raise ValidationError(_(
                    "Your quotation contains products from company %(product_company)s whereas your quotation belongs to company %(quote_company)s. \n Please change the company of your quotation or remove the products from other companies (%(bad_products)s).",
                    product_company=', '.join(invalid_companies.sudo().mapped('display_name')),
                    quote_company=order.company_id.display_name,
                    bad_products=', '.join(bad_products.mapped('display_name')),
                ))

    def _compute_access_url(self):
        super(PurchaseRfq, self)._compute_access_url()
        for order in self:
            order.access_url = '/my/purchase/%s' % (order.id)

    @api.depends('order_line.date_planned')
    def _compute_date_planned(self):
        """ date_planned = the earliest date_planned across all order lines. """
        for order in self:
            dates_list = order.order_line.filtered(lambda x: not x.display_type and x.date_planned).mapped(
                'date_planned')
            if dates_list:
                order.date_planned = min(dates_list)
            else:
                order.date_planned = False

    @api.depends('name', 'partner_ref')
    def _compute_display_name(self):
        for po in self:
            name = po.name
            if po.partner_ref:
                name += ' (' + po.partner_ref + ')'
            po.display_name = name

    @api.depends('company_id', 'partner_id')
    def _compute_receipt_reminder_email(self):
        for order in self:
            order.receipt_reminder_email = order.partner_id.with_company(order.company_id).receipt_reminder_email
            order.reminder_date_before_receipt = order.partner_id.with_company(
                order.company_id).reminder_date_before_receipt

    @api.onchange('date_planned')
    def onchange_date_planned(self):
        if self.date_planned:
            self.order_line.filtered(lambda line: not line.display_type).date_planned = self.date_planned

    def write(self, vals):
        vals, partner_vals = self._write_partner_values(vals)
        res = super().write(vals)
        if partner_vals:
            self.partner_id.sudo().write(partner_vals)  # Because the purchase user doesn't have write on `res.partner`
        return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = self.browse()
        partner_vals_list = []
        for vals in vals_list:
            company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
            self_comp = self.with_company(company_id)
            if vals.get('name', 'New') == 'New':
                seq_date = None
                if 'date_order' in vals:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
                vals['name'] = self_comp.env['ir.sequence'].next_by_code('purchase.rfq', sequence_date=seq_date) or '/'
            vals, partner_vals = self._write_partner_values(vals)
            partner_vals_list.append(partner_vals)
            orders |= super(PurchaseRfq, self_comp).create(vals)
        for order, partner_vals in zip(orders, partner_vals_list):
            if partner_vals:
                order.sudo().write(partner_vals)  # Because the purchase user doesn't have write on `res.partner`
        return orders

    @api.ondelete(at_uninstall=False)
    def _unlink_if_cancelled(self):
        for order in self:
            if not order.state == 'cancel':
                raise UserError(_('In order to delete a purchase order, you must cancel it first.'))

    def copy(self, default=None):
        ctx = dict(self.env.context)
        ctx.pop('default_product_id', None)
        self = self.with_context(ctx)
        new_po = super(PurchaseRfq, self).copy(default=default)
        for line in new_po.order_line:
            if line.product_id:
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id, quantity=line.product_qty,
                    date=line.order_id.date_order and line.order_id.date_order.date(), uom_id=line.product_uom)
                line.date_planned = line._get_date_planned(seller)
        return new_po

    def _must_delete_date_planned(self, field_name):
        # To be overridden
        return field_name == 'order_line'

    def onchange(self, values, field_names, fields_spec):
        """
        Override onchange to NOT update all date_planned on PO lines when
        date_planned on PO is updated by the change of date_planned on PO lines.
        """
        result = super().onchange(values, field_names, fields_spec)
        if any(self._must_delete_date_planned(field) for field in field_names) and 'value' in result:
            for line in result['value'].get('order_line', []):
                if line[0] == Command.UPDATE and 'date_planned' in line[2]:
                    del line[2]['date_planned']
        return result

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Purchase Order-%s' % (self.name)

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        # Ensures all properties and fiscal positions
        # are taken with the company of the order
        # if not defined, with_company doesn't change anything.
        self = self.with_company(self.company_id)
        if not self.partner_id:
            self.fiscal_position_id = False
        else:
            self.fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position(self.partner_id)
            self.payment_term_id = self.partner_id.property_supplier_payment_term_id.id
            if self.partner_id.buyer_id:
                self.user_id = self.partner_id.buyer_id
        return {}

    @api.onchange('partner_id')
    def onchange_partner_id_warning(self):
        if not self.partner_id or not self.env.user.has_group('purchase.group_warning_purchase'):
            return

        partner = self.partner_id

        # If partner has no warning, check its company
        if partner.purchase_warn == 'no-message' and partner.parent_id:
            partner = partner.parent_id

        if partner.purchase_warn and partner.purchase_warn != 'no-message':
            # Block if partner only has warning but parent company is blocked
            if partner.purchase_warn != 'block' and partner.parent_id and partner.parent_id.purchase_warn == 'block':
                partner = partner.parent_id
            title = _("Warning for %s", partner.name)
            message = partner.purchase_warn_msg
            warning = {
                'title': title,
                'message': message
            }
            if partner.purchase_warn == 'block':
                self.update({'partner_id': False})
            return {'warning': warning}
        return {}

    # ------------------------------------------------------------
    # MAIL.THREAD
    # ------------------------------------------------------------

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_rfq_as_sent'):
            self.filtered(lambda o: o.state == 'draft').write({'state': 'sent'})
        po_ctx = {'mail_post_autofollow': self.env.context.get('mail_post_autofollow', True)}
        if self.env.context.get('mark_rfq_as_sent') and 'notify_author' not in kwargs:
            kwargs['notify_author'] = self.env.user.partner_id.id in (kwargs.get('partner_ids') or [])
        return super(PurchaseRfq, self.with_context(**po_ctx)).message_post(**kwargs)

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """ Tweak 'view document' button for portal customers, calling directly
        routes for confirm specific to PO model. """
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.ensure_one()
        try:
            customer_portal_group = next(group for group in groups if group[0] == 'portal_customer')
        except StopIteration:
            pass
        else:
            access_opt = customer_portal_group[2].setdefault('button_access', {})
            if self.env.context.get('is_reminder'):
                access_opt['title'] = _('View')
                actions = customer_portal_group[2].setdefault('actions', list())
                actions.extend([
                    {'url': self.get_confirm_url(confirm_type='reminder'), 'title': _('Accept')},
                    {'url': self.get_update_url(), 'title': _('Update Dates')},
                ])
            else:
                access_opt['title'] = _('Confirm')
                access_opt['url'] = self.get_confirm_url(confirm_type='reception')

        return groups

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals=False, model_description=False,
                                                   force_email_company=False, force_email_lang=False):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang
        )
        return render_context

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'purchase':
            return self.env.ref('purchase.mt_rfq_confirmed')
        elif 'state' in init_values and self.state == 'rfq':
            return self.env.ref('purchase.mt_rfq_confirmed')
        elif 'state' in init_values and self.state == 'sent':
            return self.env.ref('purchase.mt_rfq_sent')
        return super(PurchaseRfq, self)._track_subtype(init_values)

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------


    def action_rfq_send(self):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
           template_id = ir_model_data._xmlid_lookup('purchase.email_template_edi_purchase_rfq')[1]

        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.rfq',
            'default_res_ids': self.ids,
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
            'force_email': True,
            'mark_rfq_as_sent': True,
            'default_partner_ids': [(6, 0, self.suppliers_ids.ids)],
        })

        # In the case of a RFQ, we want the "View..." button in line with the state of the
        # object. Therefore, we pass the model description in the context, in the language in which
        # the template is rendered.
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]

        self = self.with_context(lang=lang)
        if self.state in ['draft', 'sent']:
            ctx['model_description'] = _('Request for Quotation')
        else:
            ctx['model_description'] = _('Purchase Order')

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def print_quotation(self):
        return self.env.ref('purchase.report_purchase_quotation').report_action(self)

    def button_draft(self):
        self.write({'state': 'draft'})
        return {}

    def button_confirm(self):
        self.write({'state': 'rfq'})

    def button_cancel(self):
        self.write({'state': 'cancel', 'mail_reminder_confirmed': False})


    def button_creat_po(self):
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'rfq_seq': self.name,
            'partner_ref': self.partner_ref,
            'payment_term_id': self.payment_term_id.id,
            'order_line': [(0, 0, {
                'display_type': line.display_type,
                'product_id': line.product_id.id,
                'name': line.name,
                'product_qty': line.product_qty,
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

    def _prepare_supplier_info(self, partner, line):
        # Prepare supplierinfo data when adding a product
        return {
            'partner_id': partner.id,
            'sequence': max(line.product_id.seller_ids.mapped('sequence')) + 1 if line.product_id.seller_ids else 1,
            'min_qty': 1.0,
            'delay': 0,
        }

    def send_reminder_preview(self):
        self.ensure_one()
        if not self.user_has_groups('purchase.group_send_reminder'):
            return

        template = self.env.ref('purchase.email_template_edi_purchase_reminder', raise_if_not_found=False)
        if template and self.env.user.email and self.id:
            template.with_context(is_reminder=True).send_mail(
                self.id,
                force_send=True,
                raise_exception=False,
                email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
                email_values={'email_to': self.env.user.email, 'recipient_ids': []},
            )
            return {'toast_message': escape(_("A sample email has been sent to %s.", self.env.user.email))}

    def _send_reminder_open_composer(self, template_id):
        self.ensure_one()
        try:
            compose_form_id = self.env['ir.model.data']._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.rfq',
            'default_res_ids': self.ids,
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
            'force_email': True,
            'mark_rfq_as_sent': True,
        })
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]
        self = self.with_context(lang=lang)
        ctx['model_description'] = _('Purchase Order')
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def _default_order_line_values(self):
        default_data = super()._default_order_line_values()
        new_default_data = self.env['purchase.rfq.line']._get_product_catalog_lines_data()
        return {**default_data, **new_default_data}

    def _get_action_add_from_catalog_extra_context(self):
        return {
            **super()._get_action_add_from_catalog_extra_context(),
            'display_uom': self.env.user.has_group('uom.group_uom'),
            'precision': self.env['decimal.precision'].precision_get('Product Unit of Measure'),
            'search_default_seller_ids': self.partner_id.name,
        }

    def _get_product_catalog_domain(self):
        return expression.AND([super()._get_product_catalog_domain(), [('purchase_ok', '=', True)]])

    def _get_product_catalog_order_data(self, products, **kwargs):
        res = super()._get_product_catalog_order_data(products, **kwargs)
        for product in products:
            res[product.id] |= self._get_product_price_and_data(product)
        return res

    def _get_product_catalog_record_lines(self, product_ids):
        grouped_lines = defaultdict(lambda: self.env['purchase.rfq.line'])
        for line in self.order_line:
            if line.display_type or line.product_id.id not in product_ids:
                continue
            grouped_lines[line.product_id] |= line
        return grouped_lines

    def _get_product_price_and_data(self, product):
        """ Fetch the product's data used by the purchase's catalog.

        :return: the product's price and, if applicable, the minimum quantity to
                 buy and the product's packaging data.
        :rtype: dict
        """
        self.ensure_one()
        product_infos = {
            'price': product.standard_price,
            'uom': {
                'display_name': product.uom_id.display_name,
                'id': product.uom_id.id,
            },
        }
        if product.purchase_line_warn_msg:
            product_infos['warning'] = product.purchase_line_warn_msg
        if product.purchase_line_warn == "block":
            product_infos['readOnly'] = True
        if product.uom_id != product.uom_po_id:
            product_infos['purchase_uom'] = {
                'display_name': product.uom_po_id.display_name,
                'id': product.uom_po_id.id,
            }
        params = {'order_id': self}
        # Check if there is a price and a minimum quantity for the order's vendor.
        seller = product._select_seller(
            partner_id=self.partner_id,
            quantity=None,
            date=self.date_order,
            uom_id=product.uom_id,
            ordered_by='min_qty',
            params=params
        )
        if seller:
            product_infos.update(
                min_qty=seller.min_qty,
            )
        # Check if the product uses some packaging.
        packaging = self.env['product.packaging'].search(
            [('product_id', '=', product.id), ('purchase', '=', True)], limit=1
        )
        if packaging:
            qty = packaging.product_uom_id._compute_quantity(packaging.qty, product.uom_po_id)
            product_infos.update(
                packaging={
                    'id': packaging.id,
                    'name': packaging.display_name,
                    'qty': qty,
                }
            )
        return product_infos

    def get_confirm_url(self, confirm_type=None):
        """Create url for confirm reminder or purchase reception email for sending
        in mail."""
        if confirm_type in ['reminder', 'reception']:
            param = url_encode({
                'confirm': confirm_type,
                'confirmed_date': self.date_planned and (
                    self.date_planned.date() if hasattr(self.date_planned, 'date') else self.date_planned
                ),
                # 'confirmed_date': self.date_planned and self.date_planned.date(),
            })
            return self.get_portal_url(query_string='&%s' % param)
        return self.get_portal_url()

    def get_update_url(self):
        """Create portal url for user to update the scheduled date on purchase
        order lines."""
        update_param = url_encode({'update': 'True'})
        return self.get_portal_url(query_string='&%s' % update_param)

    def confirm_reminder_mail(self, confirmed_date=False):
        for order in self:
            if order.state in ['purchase', 'done'] and not order.mail_reminder_confirmed:
                order.mail_reminder_confirmed = True
                date_planned = order.get_localized_date_planned(confirmed_date).date()
                order.message_post(
                    body=_("%s confirmed the receipt will take place on %s.", order.partner_id.name, date_planned))

    def _approval_allowed(self):
        """Returns whether the order qualifies to be approved by the current user"""
        self.ensure_one()
        return (
                self.company_id.po_double_validation == 'one_step'
                or (self.company_id.po_double_validation == 'two_step'
                    or self.user_has_groups('purchase.group_purchase_manager'))
        )

    def _confirm_reception_mail(self):
        for order in self:
            if order.state in ['purchase', 'done'] and not order.mail_reception_confirmed:
                order.mail_reception_confirmed = True
                order.message_post(body=_("The order receipt has been acknowledged by %s.", order.partner_id.name))

    def get_localized_date_planned(self, date_planned=False):
        """Returns the localized date planned in the timezone of the order's user or the
        company's partner or UTC if none of them are set."""
        self.ensure_one()
        date_planned = date_planned or self.date_planned
        if not date_planned:
            return False
        if isinstance(date_planned, str):
            date_planned = fields.Date.from_string(date_planned)
        tz = self.get_order_timezone()
        return date_planned.astimezone(tz)

    def get_order_timezone(self):
        """ Returns the timezone of the order's user or the company's partner
        or UTC if none of them are set. """
        self.ensure_one()
        return timezone(self.user_id.tz or self.company_id.partner_id.tz or 'UTC')

    def _update_date_planned_for_lines(self, updated_dates):
        # create or update the activity
        activity = self.env['mail.activity'].search([
            ('summary', '=', _('Date Updated')),
            ('res_model_id', '=', 'purchase.rfq'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.user_id.id)], limit=1)
        if activity:
            self._update_update_date_activity(updated_dates, activity)
        else:
            self._create_update_date_activity(updated_dates)

        # update the date on PO line
        for line, date in updated_dates:
            line._update_date_planned(date)

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        """ Update purchase order line information for a given product or create
        a new one if none exists yet.
        :param int product_id: The product, as a `product.product` id.
        :return: The unit price of the product, based on the pricelist of the
                 purchase order and the quantity selected.
        :rtype: float
        """
        self.ensure_one()
        product_packaging_qty = kwargs.get('product_packaging_qty', False)
        product_packaging_id = kwargs.get('product_packaging_id', False)
        pol = self.order_line.filtered(lambda line: line.product_id.id == product_id)
        if pol:
            if product_packaging_qty:
                pol.product_packaging_id = product_packaging_id
                pol.product_packaging_qty = product_packaging_qty
            elif quantity != 0:
                pol.product_qty = quantity
            else:
                pol.product_qty = 0
        elif quantity > 0:
            pol = self.env['purchase.rfq.line'].create({
                'order_id': self.id,
                'product_id': product_id,
                'product_qty': quantity,
                'sequence': ((self.order_line and self.order_line[-1].sequence + 1) or 10),
                # put it at the end of the order
            })
            seller = pol.product_id._select_seller(
                partner_id=pol.partner_id,
                quantity=pol.product_qty,
                date=pol.order_id.date_order and pol.order_id.date_order.date() or fields.Date.context_today(pol),
                uom_id=pol.product_uom)

    def _create_update_date_activity(self, updated_dates):
        note = Markup('<p>%s</p>\n') % _('%s modified receipt dates for the following products:', self.partner_id.name)
        for line, date in updated_dates:
            note += Markup('<p> - %s</p>\n') % _(
                '%(product)s from %(original_receipt_date)s to %(new_receipt_date)s',
                product=line.product_id.display_name,
                original_receipt_date=line.date_planned.date(),
                new_receipt_date=date.date()
            )
        activity = self.activity_schedule(
            'mail.mail_activity_data_warning',
            summary=_("Date Updated"),
            user_id=self.user_id.id
        )
        # add the note after we post the activity because the note can be soon
        # changed when updating the date of the next PO line. So instead of
        # sending a mail with incomplete note, we send one with no note.
        activity.note = note
        return activity

    def _update_update_date_activity(self, updated_dates, activity):
        for line, date in updated_dates:
            activity.note += Markup('<p> - %s</p>\n') % _(
                '%(product)s from %(original_receipt_date)s to %(new_receipt_date)s',
                product=line.product_id.display_name,
                original_receipt_date=line.date_planned.date(),
                new_receipt_date=date.date()
            )

    def _write_partner_values(self, vals):
        partner_values = {}
        if 'receipt_reminder_email' in vals:
            partner_values['receipt_reminder_email'] = vals.pop('receipt_reminder_email')
        if 'reminder_date_before_receipt' in vals:
            partner_values['reminder_date_before_receipt'] = vals.pop('reminder_date_before_receipt')
        return vals, partner_values

    def _is_readonly(self):
        """ Return whether the purchase order is read-only or not based on the state.
        A purchase order is considered read-only if its state is 'cancel'.

        :return: Whether the purchase order is read-only or not.
        :rtype: bool
        """
        self.ensure_one()
        return self.state == 'cancel'

    # def view_related_po(self):
    #     """
    #     Open the related purchase order form view
    #     """
    #     self.ensure_one()
    #     if not self.purchase_order_id:
    #         return
    #
    #     return {
    #         'name': 'Purchase Order',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'purchase.order',
    #         'res_id': self.purchase_order_id.id,
    #         'type': 'ir.actions.act_window',
    #         'target': 'current',
    #     }
    def view_related_po(self):
        self.ensure_one()
        if not self.purchase_order_id:
            return

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_order_id.id,
            'target': 'current',
        }

    def translate_states(cr, registry):
        with api.Environment.manage():
            env = api.Environment(cr, SUPERUSER_ID, {})
            Translation = env['ir.translation']

            # For Draft state
            Translation.create({
                'name': 'purchase.rfq,state',
                'lang': 'fr_FR',
                'src': 'Draft',
                'value': 'Brouillon',
                'type': 'selection',
                'module': 'purchase',
            })

            # For Request PO state
            Translation.create({
                'name': 'purchase.rfq,state',
                'lang': 'fr_FR',
                'src': 'Request PO',
                'value': 'Demander un bon de commande',
                'type': 'selection',
                'module': 'purchase',
            })

    suppliers_ids = fields.Many2many('res.partner', string='Vendor', change_default=True, tracking=True,
                                 check_company=True, domain=[('is_supplier', '=', True)])

    @api.onchange('suppliers_ids')
    def _onchange_suppliers_ids(self):
        for record in self:
            record.partner_id = False
