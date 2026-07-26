# models/account_move_line.py
from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    use_custom_calc = fields.Boolean(
        string="Use Custom Calculation",
        compute='_compute_use_custom_calc',
        store=True,
        readonly=False,
    )

    @api.depends(
        'product_id',
        'move_id.invoice_line_ids.price_unit',
        'move_id.invoice_line_ids.quantity',
        'move_id.invoice_line_ids.discount',
        'move_id.invoice_line_ids.price_subtotal',
    )
    def _compute_use_custom_calc(self):
        for line in self:
            if line.product_id:
                line.use_custom_calc = line.product_id.product_tmpl_id.use_custom_calc
            else:
                line.use_custom_calc = False

    def _compute_totals(self):
        custom_lines = self.filtered(lambda l: l.use_custom_calc)
        regular_lines = self - custom_lines

        # Regular lines - standard Odoo calculation
        super(AccountMoveLine, regular_lines)._compute_totals()

        # Custom lines - execute custom Python code
        for line in custom_lines.sorted('sequence'):
            siblings = line.move_id.invoice_line_ids.sorted('sequence')

            # Find previous line
            prev_line = None
            for sib in siblings:
                if sib.id == line.id:
                    break
                prev_line = sib

            # Build localdict for safe_eval
            localdict = {
                'line': line,
                'move': line.move_id,
                'product': line.product_id,
                'siblings': siblings,
                'prev_line': prev_line,
                'result': 0.0,
            }

            # Execute custom code from product template
            custom_code = line.product_id.product_tmpl_id.custom_calc_code
            if custom_code:
                try:
                    safe_eval(custom_code, localdict, mode='exec', nocopy=True)
                    line.price_subtotal = localdict.get('result', 0.0)
                    line.price_total = localdict.get('result', 0.0)
                    if 'set_price_unit' in localdict:
                        line.price_unit = localdict['set_price_unit']
                except Exception as e:
                    raise ValueError(
                        f"Error in custom calculation for {line.product_id.name}: {e}"
                    )
            else:
                # No custom code defined, use standard calculation
                super(AccountMoveLine, line)._compute_totals()

    @api.onchange('quantity', 'price_unit', 'discount')
    def _onchange_line_values(self):
        """Recompute all custom calculation lines when this line changes."""
        if self.move_id and self.move_id.invoice_line_ids:
            custom_lines = self.move_id.invoice_line_ids.filtered('use_custom_calc')
            if custom_lines:
                custom_lines._compute_totals()

    display_subtotal_from_line = fields.Many2one(
        'account.move.line',
        string="Show Subtotal From Line",
        domain="[('move_id', '=', move_id)]"
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
        'move_id.invoice_line_ids',
        'move_id.invoice_line_ids.sequence',
        'move_id.invoice_line_ids.product_id',
        'move_id.use_custom_total',
        'move_id.currency_id',
    )
    def _compute_line_currency(self):
        for line in self:
            move = line.move_id
            product = line.product_id
            tmpl = product.product_tmpl_id if product else False

            if move and tmpl:
                if tmpl.currency_mode == 'computed' and tmpl.reference_product_id:
                    sorted_lines = move.invoice_line_ids.sorted(key=lambda l: (l.sequence or 0, l._origin.id or 0))
                    ref_line = sorted_lines.filtered(lambda l: l.product_id == tmpl.reference_product_id)

                    if ref_line:
                        line_list = list(sorted_lines)
                        line_idx = line_list.index(line) if line in line_list else -1
                        ref_idx = line_list.index(ref_line[0]) if ref_line[0] in line_list else -1

                        if line_idx != -1 and ref_idx != -1:
                            target_code = 'USD' if line_idx < ref_idx else 'BDT'
                            currency = self.env['res.currency'].search([('name', '=', target_code)], limit=1)
                            line.line_currency_id = currency or move.currency_id
                            continue

                if tmpl.display_currency_id:
                    line.line_currency_id = tmpl.display_currency_id
                else:
                    line.line_currency_id = move.currency_id or self.env.company.currency_id
            else:
                line.line_currency_id = move.currency_id if move else self.env.company.currency_id

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
    'move_id.print_breakdown',  # ← add this dependency
    )
    def _compute_line_type(self):
        for line in self:
            if line.display_type in ('line_section', 'line_note') or not line.product_id:
                line.line_type = False
            else:
                tmpl_line_type = line.product_id.product_tmpl_id.line_type

                if tmpl_line_type == 'conditional':
                    # Resolve based on parent move's print_breakdown flag
                    line.line_type = 'breakdown' if line.move_id.print_breakdown else 'main_invoice_only'
                else:
                    line.line_type = tmpl_line_type