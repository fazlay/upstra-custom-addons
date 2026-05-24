# models/invoice_total_type.py
from odoo import models, fields


class InvoiceTotalType(models.Model):
    _name = 'invoice.total.type'
    _description = 'Invoice Total Calculation Type'
    _order = 'name'

    name = fields.Char(required=True, string='Invoice Type')
    description = fields.Text(string='Description')
    total_code = fields.Text(
        string='Formula',
        required=True,
        help="Python code using: move, lines, result\nExample: result = sum(l.price_subtotal for l in lines)"
    )
    active = fields.Boolean(default=True)