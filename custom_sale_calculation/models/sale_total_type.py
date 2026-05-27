from odoo import models, fields


class SaleTotalType(models.Model):
    _name = 'sale.total.type'
    _description = 'Sale Order Total Calculation Type'
    _order = 'name'

    name = fields.Char(required=True, string='Total Type')
    description = fields.Text(string='Description')
    total_code = fields.Text(
        string='Formula',
        required=True,
        help="Python code using: order, lines, result\nExample: result = sum(l.price_subtotal for l in lines)"
    )
    active = fields.Boolean(default=True)
