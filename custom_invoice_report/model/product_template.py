# models/product_template.py
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    use_custom_calc = fields.Boolean(
        string="Use Custom Calculation",
        help="Enable to write custom Python logic for invoice line total calculation"
    )
    currency_mode = fields.Selection(
        [
            ('fixed', 'Fixed Currency'),
            ('computed', 'Computed (Position Relative to Reference Product)'),
        ],
        string="Display Currency Mode",
        default='fixed',
        help="Fixed: Use selected Display Currency. Computed: Currency is USD before reference product, BDT after."
    )
    display_currency_id = fields.Many2one(
        'res.currency', 
        string='Display Currency'
    )
    reference_product_id = fields.Many2one(
        'product.product',
        string='Reference Product',
        help="Select the reference product. Invoice lines placed BEFORE this product line will display in USD, lines AFTER will display in BDT."
    )
    type_code = fields.Text(
        string="Type Code")
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
- line: current account.move.line record
- move: parent account.move record
- product: product.product record (line.product_id)
- siblings: all invoice lines sorted by sequence
- prev_line: previous line in sequence (or None)
- result: SET THIS to the calculated amount (float)

Example:
# 5% local tax on lines above in same section
total = sum(l.price_subtotal for l in siblings if l.sequence < line.sequence)
result = total * 0.05
"""
    )
    
    
