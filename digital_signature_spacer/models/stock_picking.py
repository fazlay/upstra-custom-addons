# -*- coding: utf-8 -*-
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    signature_spacer = fields.Html(
        string='Signature Spacer',
        help="Add custom space or HTML content before the signature block."
    )
