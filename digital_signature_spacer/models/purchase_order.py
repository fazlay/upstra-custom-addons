# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    signature_spacer = fields.Html(
        string='Signature Spacer',
        help="Add custom space or HTML content before the signature block."
    )
