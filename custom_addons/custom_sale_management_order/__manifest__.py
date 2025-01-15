{
    'name': 'Order Sale Management Discount',
    'version': '1.0',
    'summary': 'Mở rộng chức năng giảm giá quản lý bán hàng',
    'author': 'Akdemy_Le Chinh Dai',
    'license': 'AGPL-3',
    'category': 'Sales',
    'depends': ['base', 'sale'],
    'data': [
        'views/sale_order_line_discount_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}