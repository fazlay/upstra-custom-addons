import logging

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_type_id = fields.Many2one(
        'sale.total.type',
        string='Total Calculation Type',
        help="Select a calculation method for order total",
        default=lambda self: self.env['sale.total.type'].search([], limit=1)
    )

    use_custom_total = fields.Boolean(
        string="Use Custom Total Calculation",
        help="Enable to write custom Python logic for order total"
    )
    print_breakdown = fields.Boolean(
        string="Print Items Breakdown",
        default=False
    )
    split_table_by_section = fields.Boolean(
        string="Split Table by Section",
        default=False,
        help="If true, the main order table will be split into multiple tables based on section lines."
    )
    show_bin = fields.Boolean(
        string="Show BIN",
        default=False,
        help="If enabled, the BIN number will be displayed on the report."
    )
    show_exchange_rate = fields.Boolean(
        string="Show Exchange Rate",
        default=False,
        help="If enabled, the exchange rate will be displayed on the report."
    )

    custom_total_code = fields.Text(
        string="Custom Total Formula",
        help="""
Available variables:
- order: current sale order record
- lines: all order lines (recordset)
- result: SET THIS to the calculated total amount (float)

Example:
# Sum all line subtotals
result = sum(l.price_subtotal for l in lines)
"""
    )

    custom_total = fields.Monetary(
        string="Total Amount",
        compute='_compute_custom_total',
        store=True,
        readonly=False,
    )

    @api.depends('order_line.price_subtotal', 'use_custom_total', 'custom_total_code', 'total_type_id')
    def _compute_custom_total(self):
        for order in self:
            if not order.use_custom_total:
                order.custom_total = order.amount_untaxed
                continue
            code = order.total_type_id.total_code if order.total_type_id else order.custom_total_code
            if not code:
                order.custom_total = order.amount_untaxed
                continue
            code = code.replace('line.move_id.invoice_line_ids', 'lines')
            code = code.replace('move.invoice_line_ids', 'lines')
            localdict = {
                'order': order,
                'lines': order.order_line,
                'result': 0.0,
            }
            try:
                safe_eval(code, localdict, mode='exec', nocopy=True)
                order.custom_total = localdict.get('result', order.amount_untaxed)
            except Exception as e:
                _logger.warning(
                    "Custom total calculation failed for order %s (total_type %s): %s",
                    order.id, order.total_type_id.display_name if order.total_type_id else 'N/A', e
                )
                order.custom_total = order.amount_untaxed

    def action_recalculate_custom_lines(self):
        self.ensure_one()
        if self.order_line:
            self.order_line._compute_amount()
        self._compute_custom_total()
        return True

    @api.onchange('total_type_id')
    def _onchange_total_type_id(self):
        if self.total_type_id:
            self.use_custom_total = True
            self.custom_total_code = self.total_type_id.total_code
            if self.order_line:
                self.order_line._compute_amount()
                self._compute_custom_total()
        else:
            self.use_custom_total = False
            self.custom_total_code = False

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        vals.update({
            'total_type_id': self.total_type_id.id,
            'use_custom_total': self.use_custom_total,
            'custom_total_code': self.custom_total_code,
            'print_breakdown': self.print_breakdown,
            'split_table_by_section': self.split_table_by_section,
            'show_bin': self.show_bin,
            'show_exchange_rate': self.show_exchange_rate,
        })
        return vals

    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for order in self:
            tax_totals = order.tax_totals
            if tax_totals:
                tax_totals['use_custom_total'] = order.use_custom_total
                tax_totals['custom_total'] = order.custom_total
                order.tax_totals = tax_totals
