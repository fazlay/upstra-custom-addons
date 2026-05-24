{
    'name': 'Invoice Template',
    'version': '1.0.0',
    'summary': 'Create reusable invoice templates with predefined lines',
    'depends': ['account', 'product', 'custom_invoice_report'],
    'data': [
        'security/ir.model.access.csv',
        'views/invoice_template_views.xml',
        'views/report_invoice_custom_conditional.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}