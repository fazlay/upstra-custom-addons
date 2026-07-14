# -*- coding: utf-8 -*-
{
    'name': 'Alternative Offer Generator',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Generate multiple alternative quotations from a single quotation',
    'description': """
Alternative Offer Generator for Sales
=====================================
Allows salespersons to create multiple alternative quotations from a single quotation
without affecting the existing sales workflow.
- Adjust prices and discounts of alternatives within a wizard.
- Keep alternative quotations linked to the parent quotation.
- Exclude alternative quotations from the main quotations list.
- Print all offers as a single PDF.
    """,
    'author': 'Antigravity',
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/sale_alternative_offer_wizard_views.xml',
        'views/sale_alternative_offer_report.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
