from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


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
                    raise ValueError(
                        f"Error in custom calculation for {line.product_id.name}: {e}"
                    )
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
