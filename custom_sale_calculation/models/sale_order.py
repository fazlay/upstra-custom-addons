from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_type_id = fields.Many2one(
        'sale.total.type',
        string='Total Calculation Type',
        help="Select a calculation method for order total"
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
        string="Custom Total",
        compute='_compute_custom_total',
        store=True,
        readonly=False,
    )

    @api.depends('order_line.price_subtotal', 'use_custom_total', 'custom_total_code', 'total_type_id')
    def _compute_custom_total(self):
        for order in self:
            if order.use_custom_total and (order.custom_total_code or order.total_type_id):
                localdict = {
                    'order': order,
                    'lines': order.order_line,
                    'result': 0.0,
                }
                try:
                    code = order.custom_total_code or (order.total_type_id.total_code if order.total_type_id else '')
                    if code:
                        safe_eval(code, localdict, mode='exec', nocopy=True)
                        order.custom_total = localdict.get('result', order.amount_untaxed)
                    else:
                        order.custom_total = order.amount_untaxed
                except Exception:
                    order.custom_total = order.amount_untaxed
            else:
                if not order.custom_total:
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
