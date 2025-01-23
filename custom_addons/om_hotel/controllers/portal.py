from datetime import datetime, timedelta
from odoo import http, fields
from odoo.http import request, Response
import logging
_logger = logging.getLogger(__name__)

class HotelPortal(http.Controller):
    # Hiển thị trang chủ
    # @http.route('/hotel/available_rooms', type='http', auth='user', website=True)
    # def get_available_rooms(self, **kwargs):
    #     rooms = request.env['hotel.management.room'].sudo().search([('state', '=', 'available')])
    #     return request.render('om_hotel.template_available_rooms', {'rooms': rooms})

    # API: Đặt phòng
    # @http.route('/hotel/available_rooms', type='http', auth='user', website=True)
    # def get_available_rooms(self, **kwargs):
    #     rooms = request.env['hotel.management.room'].sudo().search([('state', '=', 'available')])
    #     return request.render('om_hotel.template_available_rooms', {'rooms': rooms})

    # @http.route(['/hotel/book_room'], type='http', auth="user", website=True)
    # def book_room(self, **kwargs):
    #         rooms = request.env['hotel.management.room'].search([('state', '=', 'available')])
    #         values = {
    #             'rooms': rooms,
    #         }
    #         return request.render('om_hotel.template_available_rooms', values)
    @http.route(['/rooms'], type='http', auth="user", website=True)
    def portal_my_rooms(self, **kw):
        rooms = request.env['hotel.management.room'].search([
            ('state', '=', 'available')
        ])
        values = {
            'rooms': rooms,
        }
        return request.render("om_hotel.template_available_rooms", values)
    # @http.route(['/book/room/<int:room_id>'], type='http', auth="user", website=True)
    # def portal_booking_form(self, room_id, **kw):
    #     # Lấy thông tin phòng và các dịch vụ
    #     room = request.env['hotel.management.room'].sudo().browse(room_id)
    #     if not room.exists():
    #         return request.render("website.404")
    #     # Lấy danh sách dịch vụ (miễn phí hoặc trả phí)
    #     services = request.env['hotel.service'].sudo().search([])
    #     values = {
    #         'room': room,
    #         'services': services,
    #     }
    #     return request.render("om_hotel.portal_booking_form", values)
    @http.route(['/book/room/<int:room_id>'], type='http', auth="user", website=True)
    def portal_booking_form(self, room_id, **kw):
        room = request.env['hotel.management.room'].sudo().browse(room_id)
        if not room.exists():
            return request.render("website.404")
            # Lấy tất cả sản phẩm liên quan

        # Tách dịch vụ thành 2 loại: miễn phí và mất phí
        free_services = request.env['hotel.service'].sudo().search([('is_free', '=', True)])
        paid_services = request.env['hotel.service'].sudo().search([('is_free', '=', False)])

        values = {
            'room': room,
            'free_services': free_services,
            'paid_services': paid_services,
        }
        return request.render("om_hotel.portal_booking_form", values)

    @http.route(['/submit/booking'], type='http', auth="user", methods=['POST'], website=True)
    def submit_booking(self, **post):
            # Lấy dữ liệu từ form
            room_id = int(post.get('room_id'))
            hotel_id = int(post.get('hotel_id'))
            room_type = post.get('room_type')
            customer_name = post.get('customer_name')
            customer_id = request.env.user.partner_id.id
            check_in_date = post.get('check_in_date')
            check_out_date = post.get('check_out_date')
            payment_status = 'unpaid'
            payment_amount = 0.0

            # Tính tổng số đêm
            check_in = fields.Date.from_string(check_in_date)
            check_out = fields.Date.from_string(check_out_date)
            number_of_nights = (check_out - check_in).days

            # Dịch vụ được chọn
            service_ids = post.get('services')
            service_lines = []
            if isinstance(service_ids, list):
                for service_id in service_ids:
                    service = request.env['hotel.service'].sudo().browse(int(service_id))
                    if service:
                        service_lines.append((0, 0, {
                            'service_id': service.id,
                            'price': service.price,
                            'unit_price': service.unit_price,
                        }))
            # Tạo Booking Reference thủ công (ví dụ: sử dụng thời gian và ID người dùng)
            booking_reference = f"BOOK-{request.env.user.id}-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Tạo booking
            booking = request.env['hotel.management.booking'].sudo().create({
                'name': booking_reference,  # Gán Booking Reference thủ công
                'room_id': room_id,
                'hotel_id': hotel_id,
                'room_type': room_type,
                'customer_name': customer_name,
                'customer_id': customer_id,
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'state': 'draft',
                'payment_status': payment_status,
                'payment_amount': payment_amount,
                'number_of_nights': number_of_nights,
                'service_ids': service_lines,
            })

            # Cập nhật trạng thái phòng thành "Booked"
            booking.room_id.state = 'booked'
            return request.redirect('/my/bookings')

    @http.route(['/my/bookings'], type='http', auth="user", website=True)
    def portal_my_bookings(self, **kw):
        # Lấy danh sách booking của khách hàng hiện tại
        bookings = request.env['hotel.management.booking'].sudo().search([
            ('customer_id', '=', request.env.user.partner_id.id),
        ])

        values = {
            'bookings': bookings,
        }
        return request.render("om_hotel.portal_my_bookings", values)
