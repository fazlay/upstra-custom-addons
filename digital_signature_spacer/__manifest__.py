# -*- coding: utf-8 -*-
{
    'name': 'Digital Signature Spacer',
    'version': '18.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Add an HTML spacer before the signature in reports and forms',
    'description': """
        This module extends the Digital Signature module to add a customizable HTML spacer field
        before the signature block. This allows users to control the space/layout before the signature in reports.
    """,
    'author': 'Antigravity',
    'depends': ['digital_signature', 'purchase', 'stock', 'account'],
    'data': [
        'views/account_move_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
        'report/invoice_report_templates.xml',
        'report/purchase_report_templates.xml',
        'report/stock_picking_report_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
