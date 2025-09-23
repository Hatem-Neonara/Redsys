# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_stamp_exempt = fields.Boolean(
        related='partner_id.is_stamp_exempt',
        string="Exonéré Timbre",
        store=False,
        help="Indique si le partenaire est exonéré de la taxe de timbre fiscal"
    )

    # ---- compat recalcul échéances / receivable-payable
    def _recompute_terms_safe(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        if hasattr(self, "_recompute_dynamic_lines"):
            return self._recompute_dynamic_lines(
                recompute_all_taxes=recompute_all_taxes,
                recompute_tax_base_amount=recompute_tax_base_amount,
            )
        if hasattr(self, "_recompute_payment_terms_lines"):
            return self._recompute_payment_terms_lines()
        if hasattr(self, "_onchange_invoice_payment_term_id"):
            return self._onchange_invoice_payment_term_id()
        return None

    def _find_stamp_tax(self):
        domain = [('company_id', '=', self.company_id.id), ('amount_type', '=', 'fixed')]
        tax = self.env['account.tax'].search(domain + [('invoice_label', '=', '1DT')], limit=1)
        if tax:
            return tax
        return self.env['account.tax'].search(domain + [('name', 'ilike', 'timbre')], limit=1)

    # ---- helper: créer / mettre à jour la vraie tax line
    def _add_or_update_stamp_tax_line(self, stamp_tax):
        self.ensure_one()

        # 1) Obtenir montant et méta via compute_all (même si base=0, taxe fixe donne un montant)
        tax_res = stamp_tax.compute_all(
            0.0, currency=self.currency_id, quantity=1.0, product=None, partner=self.partner_id
        )
        if not tax_res.get('taxes'):
            return

        t = tax_res['taxes'][0]
        amount = t['amount']
        tax_id = t['id']
        repart_id = t.get('tax_repartition_line_id')
        account_id = t.get('account_id')
        if not (repart_id and account_id):
            raise UserError(_("Taxe timbre mal configurée (compte/répartition manquants)."))

        # 2) Sens débit/crédit
        def drcr(val, mt):
            if mt in ('out_invoice', 'out_refund'):
                return {'debit': max(0.0, -val), 'credit': max(0.0, val)}
            else:  # in_invoice / in_refund
                return {'debit': max(0.0, val), 'credit': max(0.0, -val)}

        # 3) Préparer valeurs de la tax line
        terms = self.line_ids.filtered(lambda l: l.display_type == 'payment_term')[:1]
        partner_id = terms.partner_id.id if terms else self.partner_id.id

        vals = {
            'name': "Droit de Timbre",
            'display_type': 'tax',
            'tax_line_id': tax_id,
            'tax_repartition_line_id': repart_id,
            'account_id': account_id,
            'quantity': 1.0,
            'price_unit': amount,
            'partner_id': partner_id,
            'company_id': self.company_id.id,
            'date': self.invoice_date or fields.Date.context_today(self),
            **drcr(amount, self.move_type),
        }

        # 4) Supprimer/mettre à jour les anciennes lignes de timbre (tax lines)
        old_tax_lines = self.line_ids.filtered(
            lambda l: l.display_type == 'tax' and l.tax_line_id and l.tax_line_id.id == tax_id
        )
        in_onchange = (self != self._origin)

        if old_tax_lines:
            old_tax_lines.write(vals)
        else:
            create_method = in_onchange and self.env['account.move.line'].new or self.env['account.move.line'].create
            new_line = create_method(dict(vals, move_id=(self.id if not in_onchange else self._origin)))
            if in_onchange:
                self.line_ids += new_line

    # ---- ONCHANGE principal
    @api.onchange('is_stamp_exempt', 'partner_id')
    def _onchange_add_fiscal_stamp(self):
        if self.move_type not in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund') or self.state != 'draft':
            return

        stamp_tax = self._find_stamp_tax()
        if not stamp_tax:
            return

        # Nettoyer: enlever toute ancienne "tax line" de timbre
        old_tax_lines = self.line_ids.filtered(
            lambda l: l.display_type == 'tax' and l.tax_line_id and l.tax_line_id.id == stamp_tax.id
        )
        if old_tax_lines:
            self.line_ids = self.line_ids - old_tax_lines

        # Exonéré -> ne rien ajouter, juste réaligner
        if self.is_stamp_exempt:
            self._recompute_terms_safe(False, False)
            return

        # Ajouter ou mettre à jour la vraie ligne de taxe
        self._add_or_update_stamp_tax_line(stamp_tax)

        # Réaligner échéances / receivable-payable
        self._recompute_terms_safe(False, False)

    # ---- create / write inchangés
    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if rec.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund') and rec.state == 'draft':
            rec._onchange_add_fiscal_stamp()
        return rec

    def write(self, vals):
        res = super().write(vals)
        if 'partner_id' in vals or 'is_stamp_exempt' in vals:
            for rec in self:
                if rec.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund') and rec.state == 'draft':
                    rec._onchange_add_fiscal_stamp()
        return res

    def _ensure_payment_term_balance(self):
        """
        Si, après ajout/suppression de la tax line, l'écriture est déséquilibrée,
        on ajuste/crée une ligne payment_term pour équilibrer le move.
        """
        for move in self:
            if move.state != 'draft' or not move.is_invoice(include_receipts=True):
                continue

            # Diff global selon la devise société (plus sûr pour le post)
            debit = sum(move.line_ids.mapped('debit')) or 0.0
            credit = sum(move.line_ids.mapped('credit')) or 0.0
            diff = move.company_currency_id.round(debit - credit)

            if abs(diff) < (move.company_currency_id.rounding or 0.01):
                continue  # déjà équilibré

            # Déterminer le compte de contrepartie (client/fournisseur)
            partner = move.partner_id.with_company(move.company_id)
            if move.is_sale_document(include_receipts=True):
                account = partner.property_account_receivable_id or move.journal_id.default_account_id
            else:
                account = partner.property_account_payable_id or move.journal_id.default_account_id
            if not account:
                raise UserError(_("Aucun compte de contrepartie configuré (client/fournisseur ou journal)."))

            # Déterminer sens complémentaire
            if diff < 0:
                # Trop de crédits => on ajoute du DEBIT
                delta_vals = {'debit': -diff, 'credit': 0.0}
            else:
                # Trop de débits => on ajoute du CREDIT
                delta_vals = {'debit': 0.0, 'credit': diff}

            # S'appuyer sur une ligne payment_term existante si possible
            pt_lines = move.line_ids.filtered(lambda l: l.display_type == 'payment_term')
            in_onchange = (move != move._origin)

            if pt_lines:
                # Ajuster la 1ère ligne d'échéance
                line = pt_lines[0]
                line.write({
                    'debit': (line.debit or 0.0) + delta_vals['debit'],
                    'credit': (line.credit or 0.0) + delta_vals['credit'],
                })
            else:
                # Créer une ligne payment_term pour équilibrer
                vals = {
                    'name': _('Balance'),
                    'display_type': 'payment_term',
                    'account_id': account.id,
                    'partner_id': move.partner_id.id,
                    'company_id': move.company_id.id,
                    'date': move.invoice_date or fields.Date.context_today(move),
                    **delta_vals,
                }
                create_method = in_onchange and self.env['account.move.line'].new or self.env[
                    'account.move.line'].create
                new_line = create_method(dict(vals, move_id=(move.id if not in_onchange else move._origin)))
                if in_onchange:
                    move.line_ids += new_line

        # --- helper: identifier la taxe timbre ---

    def _is_stamp_tax(self, tax):
        """Détecte la taxe timbre: flag custom is_stamp, ou étiquette 1DT, ou nom 'timbre'."""
        return bool(
            getattr(tax, 'is_stamp', False) or
            (getattr(tax, 'invoice_label', '') == '1DT') or
            ('timbre' in (tax.name or '').lower())
        )

        # --- SURCHARGE: injecter le timbre dans tax_totals ---

    def _compute_tax_totals(self):
        super()._compute_tax_totals()  # garde le calcul standard
        for move in self:
            if not move.is_invoice(include_receipts=True) or not move.tax_totals:
                continue

            totals = move.tax_totals
            currency = move.currency_id or move.company_id.currency_id

            # Déjà présent ? (éviter double comptage si un autre module l’a injecté)
            groups_map = totals.get('groups_by_subtotal') or {}
            already_has_stamp = any(
                any('timbre' in (g.get('tax_group_name', '').lower()) for g in groups)
                for _, groups in groups_map.items()
            )
            if already_has_stamp:
                continue

            # Récupérer les tax lines de timbre
            stamp_lines = move.line_ids.filtered(
                lambda l: l.display_type == 'tax' and l.tax_line_id and self._is_stamp_tax(l.tax_line_id)
            )
            if not stamp_lines:
                continue

            # Somme du timbre en devise de la facture (amount_currency est signé; on prend la valeur absolue)
            stamp_amount = sum(abs(l.amount_currency or 0.0) for l in stamp_lines)
            if not stamp_amount:
                continue

            # Déterminer le groupe de taxe (pour l’UI)
            stamp_tax = stamp_lines[0].tax_line_id
            tax_group_id = getattr(stamp_tax, 'tax_group_id', False).id if getattr(stamp_tax, 'tax_group_id',
                                                                                   False) else False

            # Clé de sous-total cible (on s'accroche au 1er existant)
            subtotals_order = totals.get('subtotals_order') or []
            first_key = subtotals_order[0] if subtotals_order else (next(iter(groups_map.keys()), None))
            if not first_key:
                # Sécuriser la structure au besoin
                totals.setdefault('groups_by_subtotal', {})
                first_key = 'base'
                totals['groups_by_subtotal'].setdefault(first_key, [])

            # Entrée de groupe complète (tous les champs monétaires requis)
            group_entry = {
                'tax_group_id': tax_group_id,
                'tax_group_name': _("Timbre fiscal"),
                'tax_group_amount': stamp_amount,  # montant taxe à afficher
                'tax_group_base_amount': 0.0,  # ⚠️ DOIT être numérique
                'formatted_tax_group_amount': formatLang(self.env, stamp_amount, currency_obj=currency),
                'formatted_tax_group_base_amount': formatLang(self.env, 0.0, currency_obj=currency),
            }
            totals['groups_by_subtotal'].setdefault(first_key, []).append(group_entry)

            # Mettre à jour les totaux généraux
            totals['amount_tax'] = (totals.get('amount_tax') or 0.0) + stamp_amount
            totals['formatted_amount_tax'] = formatLang(self.env, totals['amount_tax'], currency_obj=currency)

            totals['amount_total'] = (totals.get('amount_total') or 0.0) + stamp_amount
            totals['formatted_amount_total'] = formatLang(self.env, totals['amount_total'], currency_obj=currency)

            # Réaffecter (certaines bases veulent une réécriture explicite)
            move.tax_totals = totals
