import logging

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    use_custom_calc = fields.Boolean(
        string="Use Custom Calculation",
        compute='_compute_use_custom_calc',
        store=True,
        readonly=False,
    )

    @api.depends(
        'product_id',
        'order_id.order_line.price_unit',
        'order_id.order_line.product_uom_qty',
        'order_id.order_line.discount',
        'order_id.order_line.price_subtotal',
    )
    def _compute_use_custom_calc(self):
        for line in self:
            if line.product_id:
                line.use_custom_calc = line.product_id.product_tmpl_id.use_custom_calc
            else:
                line.use_custom_calc = False

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        custom_lines = self.filtered(lambda l: l.use_custom_calc)
        regular_lines = self - custom_lines

        super(SaleOrderLine, regular_lines)._compute_amount()

        for line in custom_lines.sorted('sequence'):
            siblings = line.order_id.order_line.sorted('sequence')

            prev_line = None
            for sib in siblings:
                if sib.id == line.id:
                    break
                prev_line = sib

            localdict = {
                'line': line,
                'order': line.order_id,
                'move': line.order_id,
                'product': line.product_id,
                'siblings': siblings,
                'prev_line': prev_line,
                'result': 0.0,
            }

            custom_code = line.product_id.product_tmpl_id.custom_calc_code
            if custom_code:
                try:
                    code = custom_code
                    code = code.replace(
                        'line.move_id.invoice_line_ids',
                        'line.order_id.order_line'
                    )
                    code = code.replace(
                        'move.invoice_line_ids',
                        'order.order_line'
                    )
                    safe_eval(code, localdict, mode='exec', nocopy=True)
                    line.price_subtotal = localdict.get('result', 0.0)
                    line.price_total = localdict.get('result', 0.0)
                    if 'set_price_unit' in localdict:
                        line.price_unit = localdict['set_price_unit']
                except Exception as e:
                    _logger.warning(
                        "Custom calc failed for line %s (%s, product %s): %s",
                        line.id, line.display_name, line.product_id.display_name, e
                    )
                    super(SaleOrderLine, line)._compute_amount()
            else:
                super(SaleOrderLine, line)._compute_amount()

    @api.onchange('product_uom_qty', 'price_unit', 'discount')
    def _onchange_line_values(self):
        if self.order_id and self.order_id.order_line:
            custom_lines = self.order_id.order_line.filtered('use_custom_calc')
            if custom_lines:
                custom_lines._compute_amount()

    display_subtotal_from_line = fields.Many2one(
        'sale.order.line',
        string="Show Subtotal From Line",
        domain="[('order_id', '=', order_id)]"
    )

    line_currency_id = fields.Many2one(
        'res.currency',
        compute='_compute_line_currency',
        store=False,
        readonly=True,
    )

    @api.depends(
        'product_id',
        'product_id.display_currency_id',
        'product_id.currency_mode',
        'product_id.reference_product_id',
        'order_id.order_line',
        'order_id.order_line.sequence',
        'order_id.order_line.product_id',
        'order_id.use_custom_total',
        'order_id.currency_id',
    )
    def _compute_line_currency(self):
        for line in self:
            order = line.order_id
            product = line.product_id
            tmpl = product.product_tmpl_id if product else False

            if order and tmpl:
                if tmpl.currency_mode == 'computed' and tmpl.reference_product_id:
                    sorted_lines = order.order_line.sorted(key=lambda l: (l.sequence or 0, l._origin.id or 0))
                    ref_line = sorted_lines.filtered(lambda l: l.product_id == tmpl.reference_product_id)

                    if ref_line:
                        line_list = list(sorted_lines)
                        line_idx = line_list.index(line) if line in line_list else -1
                        ref_idx = line_list.index(ref_line[0]) if ref_line[0] in line_list else -1

                        if line_idx != -1 and ref_idx != -1:
                            target_code = 'USD' if line_idx < ref_idx else 'BDT'
                            currency = self.env['res.currency'].search([('name', '=', target_code)], limit=1)
                            line.line_currency_id = currency or order.currency_id
                            continue

                if tmpl.display_currency_id:
                    line.line_currency_id = tmpl.display_currency_id
                else:
                    line.line_currency_id = order.currency_id or self.env.company.currency_id
            else:
                line.line_currency_id = order.currency_id if order else self.env.company.currency_id

    line_type = fields.Selection(
        [('main_invoice_only', 'Invoice'), ('breakdown', 'Items Breakdown'), ('both', 'Both')],
        string="Line Type",
        compute="_compute_line_type",
        store=False
    )

    @api.depends(
        'product_id',
        'product_id.product_tmpl_id.line_type',
        'display_type',
        'order_id.print_breakdown',
    )
    def _compute_line_type(self):
        for line in self:
            if line.display_type in ('line_section', 'line_note') or not line.product_id:
                line.line_type = False
            else:
                tmpl_line_type = line.product_id.product_tmpl_id.line_type
                if tmpl_line_type == 'conditional':
                    line.line_type = 'breakdown' if line.order_id.print_breakdown else 'main_invoice_only'
                else:
                    line.line_type = tmpl_line_type
