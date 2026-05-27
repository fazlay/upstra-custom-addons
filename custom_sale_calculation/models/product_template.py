from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    use_custom_calc = fields.Boolean(
        string="Use Custom Calculation",
        help="Enable to write custom Python logic for sale order line total calculation"
    )
    display_currency_id = fields.Many2one(
        'res.currency',
        string='Display Currency'
    )
    type_code = fields.Text(string="Type Code")
    line_type = fields.Selection(
        [
            ('main_invoice_only', 'Invoice'),
            ('breakdown', 'Items Breakdown'),
            ('conditional', 'Conditional'),
            ('both', 'Both'),
        ],
        string="Line Type",
        default='main_invoice_only'
    )
    custom_calc_code = fields.Text(
        string="Custom Calculation Code",
        help="""
Available variables in the code:
- line: current sale.order.line record
- order: parent sale.order record
- product: product.product record (line.product_id)
- siblings: all order lines sorted by sequence
- prev_line: previous line in sequence (or None)
- result: SET THIS to the calculated amount (float)

Example:
# 5% local tax on lines above in same section
total = sum(l.price_subtotal for l in siblings if l.sequence < line.sequence)
result = total * 0.05
"""
    )
