from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class AccountMove(models.Model):
    _inherit = "account.move"

    total_type_id = fields.Many2one(
        'invoice.total.type',
        string='Total Total Type',
        help="Select a calculation method for invoice total"
    )

    use_custom_total = fields.Boolean(
        string="Use Custom Total Calculation",
        help="Enable to write custom Python logic for invoice total"
    )
    print_breakdown = fields.Boolean(
        string="Print Items Breakdown",
        default=False
    )
    split_table_by_section = fields.Boolean(
        string="Split Table by Section",
        default=False,
        help="If true, the main invoice table will be split into multiple tables based on section lines."
    )
    show_bin = fields.Boolean(
        string="Show BIN",
        default=False,
        help="If enabled, the BIN number will be displayed on the invoice report."
    )
    show_exchange_rate = fields.Boolean(
        string="Show Exchange Rate",
        default=False,
        help="If enabled, the exchange rate will be displayed on the invoice report."
    )

    custom_total_code = fields.Text(
        string="Custom Total Formula",
        help="""
Available variables:
- move: current invoice record
- lines: all invoice lines (recordset)
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

    @api.depends('invoice_line_ids.price_subtotal', 'use_custom_total', 'custom_total_code', 'total_type_id')
    def _compute_custom_total(self):
        for move in self:
            # Only recompute if using a custom formula (code or total_type)
            if move.use_custom_total and (move.custom_total_code or move.total_type_id):
                localdict = {
                    'move': move,
                    'lines': move.invoice_line_ids,
                    'result': 0.0,
                }

                try:
                    code = move.custom_total_code or (move.total_type_id.total_code if move.total_type_id else '')
                    if code:
                        safe_eval(code, localdict, mode='exec', nocopy=True)
                        move.custom_total = localdict.get('result', move.amount_untaxed)
                    else:
                        move.custom_total = move.amount_untaxed
                except Exception as e:
                    move.custom_total = move.amount_untaxed
            else:
                # If no custom formula, don't override manual entry
                if not move.custom_total:
                    move.custom_total = move.amount_untaxed

    def action_recalculate_custom_lines(self):
        """Recalculate all custom calculation lines in this invoice."""
        self.ensure_one()
        if self.invoice_line_ids:
            self.invoice_line_ids._compute_totals()
        self._compute_custom_total()
        return True

    @api.onchange('total_type_id')
    def _onchange_total_type_id(self):
        """Auto-fill custom total when total type is selected."""
        if self.total_type_id:
            self.use_custom_total = True
            self.custom_total_code = self.total_type_id.total_code
            # Trigger recompute
            if self.invoice_line_ids:
                self.invoice_line_ids._compute_totals()
                self._compute_custom_total()