{
    "name": "Hotel Management System",
    "author": "Akdemy_Le Chinh Dai",
    "license": "LGPL-3",
    "version": "18.0.1.0",
    'depends': ['base', 'website', 'mail', 'hr', 'portal' ,'account', 'product', 'sale', 'stock', 'point_of_sale'],
    'data': [
        # Security
        'security/hotel_security.xml',
        'data/hotel_users.xml',
        'security/hotel_record_rules.xml',
        'security/ir.model.access.csv',
        # 'data/email_templates.xml',
        'data/ir_cron_data.xml',  # Cron job


        # Data
        'templates/portal_templates.xml',
        # Views
        'views/hotel_views.xml',
        'views/room_views.xml',
        'views/room_feature_views.xml',
        'views/booking_views.xml',
        'views/booking_payment_wizard_views.xml',
        'views/report.xml',
        'views/report_booking_template.xml',
        'views/stock_view.xml',
        'views/customer_available_rooms_template.xml',
        'views/hotel_report_views.xml',
        # 'views/customer_services_templates.xml',
        # 'views/hotel_employee_views.xml',
        # 'views/hotel_report_wizard.xml',
        # 'views/hotel_revenue_report.xml',
        # 'views/report_hotel_room.xml',
        # 'views/product_view_inherit.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hotel_management/static/src/js/pos_hotel.js',
        ],
    },
    'test': [
        'tests/test_booking_access.py',
    ],

    'application': True,
    'installable': True,

}