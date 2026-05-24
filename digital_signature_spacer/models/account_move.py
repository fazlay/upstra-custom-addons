# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    signature_spacer = fields.Html(
        string='Signature Spacer',
        help="Add custom space or HTML content before the signature block."
    )
