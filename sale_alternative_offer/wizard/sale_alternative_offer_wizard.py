# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class SaleAlternativeOfferWizard(models.TransientModel):
    _name = 'sale.alternative.offer.wizard'
    _description = 'Generate Alternative Offers Wizard'

    sale_order_id = fields.Many2one(
        'sale.order', 
        string='Original Quotation', 
        required=True, 
        ondelete='cascade'
    )
    partner_id = fields.Many2one(
        'res.partner', 
        string='Customer', 
        related='sale_order_id.partner_id'
    )
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency', 
        related='sale_order_id.currency_id'
    )

    original_line_ids = fields.One2many(
        'sale.alternative.offer.wizard.line.original', 
        'wizard_id', 
        string='Original Lines'
    )

    alternative_1_title = fields.Char(
        string='Alternative 1 Title', 
        required=True, 
        default='Alternative 1'
    )
    alternative_1_line_ids = fields.One2many(
        'sale.alternative.offer.wizard.line.alt1', 
        'wizard_id', 
        string='Alternative 1 Lines'
    )
    alternative_1_amount_untaxed = fields.Monetary(
        string='Alternative 1 Untaxed Total', 
        compute='_compute_alt1_totals', 
        currency_field='currency_id'
    )
    alternative_1_amount_tax = fields.Monetary(
        string='Alternative 1 Tax', 
        compute='_compute_alt1_totals', 
        currency_field='currency_id'
    )
    alternative_1_amount_total = fields.Monetary(
        string='Alternative 1 Grand Total', 
        compute='_compute_alt1_totals', 
        currency_field='currency_id'
    )

    alternative_2_title = fields.Char(
        string='Alternative 2 Title', 
        required=True, 
        default='Alternative 2'
    )
    alternative_2_line_ids = fields.One2many(
        'sale.alternative.offer.wizard.line.alt2', 
        'wizard_id', 
        string='Alternative 2 Lines'
    )
    alternative_2_amount_untaxed = fields.Monetary(
        string='Alternative 2 Untaxed Total', 
        compute='_compute_alt2_totals', 
        currency_field='currency_id'
    )
    alternative_2_amount_tax = fields.Monetary(
        string='Alternative 2 Tax', 
        compute='_compute_alt2_totals', 
        currency_field='currency_id'
    )
    alternative_2_amount_total = fields.Monetary(
        string='Alternative 2 Grand Total', 
        compute='_compute_alt2_totals', 
        currency_field='currency_id'
    )

    @api.depends('alternative_1_line_ids.price_subtotal', 'alternative_1_line_ids.price_total')
    def _compute_alt1_totals(self):
        for wizard in self:
            untaxed = sum(line.price_subtotal for line in wizard.alternative_1_line_ids)
            total = sum(line.price_total for line in wizard.alternative_1_line_ids)
            wizard.alternative_1_amount_untaxed = untaxed
            wizard.alternative_1_amount_total = total
            wizard.alternative_1_amount_tax = total - untaxed

    @api.depends('alternative_2_line_ids.price_subtotal', 'alternative_2_line_ids.price_total')
    def _compute_alt2_totals(self):
        for wizard in self:
            untaxed = sum(line.price_subtotal for line in wizard.alternative_2_line_ids)
            total = sum(line.price_total for line in wizard.alternative_2_line_ids)
            wizard.alternative_2_amount_untaxed = untaxed
            wizard.alternative_2_amount_total = total
            wizard.alternative_2_amount_tax = total - untaxed

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order_id = self.env.context.get('default_sale_order_id') or self.env.context.get('active_id')
        if order_id:
            order = self.env['sale.order'].browse(order_id)
            res['sale_order_id'] = order.id
            res['alternative_1_title'] = _('Alternative 1')
            res['alternative_2_title'] = _('Alternative 2')

            original_lines = []
            alt1_lines = []
            alt2_lines = []

            for line in order.order_line:
                if line.display_type:
                    continue
                line_vals = {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                    'tax_ids': [(6, 0, line.tax_id.ids)],
                    'original_line_id': line.id,
                }
                original_lines.append((0, 0, line_vals))
                alt1_lines.append((0, 0, line_vals.copy()))
                alt2_lines.append((0, 0, line_vals.copy()))

            res['original_line_ids'] = original_lines
            res['alternative_1_line_ids'] = alt1_lines
            res['alternative_2_line_ids'] = alt2_lines
        return res

    def action_generate_offers(self):
        self.ensure_one()
        original_order = self.sale_order_id

        # 1. Create Alternative 1
        alt1_order = original_order.copy(default={
            'parent_sale_order_id': original_order.id,
            'is_alternative_offer': True,
            'offer_name': self.alternative_1_title,
        })
        self._update_cloned_order_prices(original_order, alt1_order, self.alternative_1_line_ids)

        # 2. Create Alternative 2
        alt2_order = original_order.copy(default={
            'parent_sale_order_id': original_order.id,
            'is_alternative_offer': True,
            'offer_name': self.alternative_2_title,
        })
        self._update_cloned_order_prices(original_order, alt2_order, self.alternative_2_line_ids)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _update_cloned_order_prices(self, original_order, cloned_order, wizard_lines):
        # Sort both original and cloned lines to match them one-to-one
        original_lines = original_order.order_line.sorted(key=lambda l: (l.sequence, l.id))
        cloned_lines = cloned_order.order_line.sorted(key=lambda l: (l.sequence, l.id))

        line_mapping = {}
        for orig, clone in zip(original_lines, cloned_lines):
            line_mapping[orig.id] = clone

        for w_line in wizard_lines:
            if w_line.original_line_id:
                cloned_line = line_mapping.get(w_line.original_line_id.id)
                if cloned_line:
                    cloned_line.write({
                        'price_unit': w_line.price_unit,
                        'discount': w_line.discount,
                    })


class SaleAlternativeOfferWizardLineOriginal(models.TransientModel):
    _name = 'sale.alternative.offer.wizard.line.original'
    _description = 'Original Offer Wizard Line'

    wizard_id = fields.Many2one('sale.alternative.offer.wizard', string='Wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Char(string='Description')
    product_uom_qty = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price')
    discount = fields.Float(string='Discount')
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_amounts', currency_field='currency_id')
    price_total = fields.Monetary(string='Total', compute='_compute_amounts', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', related='wizard_id.currency_id')
    original_line_id = fields.Many2one('sale.order.line', string='Original Line')

    @api.depends('price_unit', 'product_uom_qty', 'discount', 'tax_ids')
    def _compute_amounts(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            partner = line.wizard_id.partner_id
            currency = line.wizard_id.currency_id
            taxes = line.tax_ids.compute_all(
                price,
                currency=currency,
                quantity=line.product_uom_qty,
                product=line.product_id,
                partner=partner
            )
            line.price_subtotal = taxes['total_excluded']
            line.price_total = taxes['total_included']


class SaleAlternativeOfferWizardLineAlt1(models.TransientModel):
    _name = 'sale.alternative.offer.wizard.line.alt1'
    _description = 'Alternative 1 Offer Wizard Line'

    wizard_id = fields.Many2one('sale.alternative.offer.wizard', string='Wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Char(string='Description')
    product_uom_qty = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price')
    discount = fields.Float(string='Discount')
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_amounts', currency_field='currency_id')
    price_total = fields.Monetary(string='Total', compute='_compute_amounts', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', related='wizard_id.currency_id')
    original_line_id = fields.Many2one('sale.order.line', string='Original Line')

    @api.depends('price_unit', 'product_uom_qty', 'discount', 'tax_ids')
    def _compute_amounts(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            partner = line.wizard_id.partner_id
            currency = line.wizard_id.currency_id
            taxes = line.tax_ids.compute_all(
                price,
                currency=currency,
                quantity=line.product_uom_qty,
                product=line.product_id,
                partner=partner
            )
            line.price_subtotal = taxes['total_excluded']
            line.price_total = taxes['total_included']


class SaleAlternativeOfferWizardLineAlt2(models.TransientModel):
    _name = 'sale.alternative.offer.wizard.line.alt2'
    _description = 'Alternative 2 Offer Wizard Line'

    wizard_id = fields.Many2one('sale.alternative.offer.wizard', string='Wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Char(string='Description')
    product_uom_qty = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price')
    discount = fields.Float(string='Discount')
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_amounts', currency_field='currency_id')
    price_total = fields.Monetary(string='Total', compute='_compute_amounts', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', related='wizard_id.currency_id')
    original_line_id = fields.Many2one('sale.order.line', string='Original Line')

    @api.depends('price_unit', 'product_uom_qty', 'discount', 'tax_ids')
    def _compute_amounts(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            partner = line.wizard_id.partner_id
            currency = line.wizard_id.currency_id
            taxes = line.tax_ids.compute_all(
                price,
                currency=currency,
                quantity=line.product_uom_qty,
                product=line.product_id,
                partner=partner
            )
            line.price_subtotal = taxes['total_excluded']
            line.price_total = taxes['total_included']
