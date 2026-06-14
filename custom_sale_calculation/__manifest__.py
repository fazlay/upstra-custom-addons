{
    'name': 'Custom Sale Calculation',
    'version': '18.0.1.0.0',
    'summary': 'Custom calculation for sale order lines with selectable total methods',
    'depends': ['sale', 'product', 'custom_invoice_report'],
    'data': [
        'security/ir.model.access.csv',
        # 'data/total_types.xml',
        # 'report/report_saleorder.xml',
        'views/sale_order_views.xml',
        'views/sale_total_type_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
