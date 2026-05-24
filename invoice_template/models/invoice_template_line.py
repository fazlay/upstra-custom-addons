# models/invoice_template_line.py
from odoo import fields, models


class InvoiceTemplateLine(models.Model):
    _name = 'invoice.template.line'
    _description = 'Invoice Template Line'
    _order = 'sequence'

    template_id = fields.Many2one(
        'invoice.template',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10, string='Line Number')
    product_id = fields.Many2one(
        'product.product',
        required=True,
        string='Product'
    )
    name = fields.Text(string='Description')
    quantity = fields.Float(default=1.0, string='Quantity')
    price_unit = fields.Float(string='Unit Price')