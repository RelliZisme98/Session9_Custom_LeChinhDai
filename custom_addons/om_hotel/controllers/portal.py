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
    @http.route(['/book/room/<int:room_id>'], type='http', auth="user", website=True)
    def portal_booking_form(self, room_id, **kw):
        # Lấy thông tin phòng và các dịch vụ
        room = request.env['hotel.management.room'].sudo().browse(room_id)
        if not room.exists():
            return request.render("website.404")

        services = request.env['hotel.service'].sudo().search([])
        values = {
            'room': room,
            'services': services,
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

    # @http.route('/hotel/book_room', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    # def book_room(self, room_id, check_in_date, check_out_date, **kwargs):
    #     _logger.info(f"Request session: {request.session}")
    #     _logger.info(f"CSRF token: {request.csrf_token()}")
    #     _logger.info(f"Form data: {kwargs}")
    #     room = request.env['hotel.management.room'].sudo().browse(room_id)
    #     if not room.exists() or room.state != 'available':
    #         return Response({'error': 'Room is not available'}, status=400)
    #
    #     if check_out_date <= check_in_date:
    #         return Response({'error': 'Invalid check-in or check-out date'}, status=400)
    #
    #     check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
    #     check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    #     delta_days = (check_out - check_in).days
    #     weekday_total = 0
    #     weekend_total = 0
    #
    #     for day in range(delta_days):
    #         current_day = check_in + timedelta(days=day)
    #         if current_day.weekday() in [5, 6]:
    #             weekend_total += room.weekend_price
    #         else:
    #             weekday_total += room.weekday_price
    #
    #     # Tạo booking mới
    #         booking = request.env['hotel.management.booking'].sudo().create({
    #         'customer_id': request.env.user.partner_id.id,
    #         'customer_name': request.env.user.name,
    #         'room_id': room.id,
    #         'check_in_date': check_in_date,
    #         'check_out_date': check_out_date,
    #         'state': 'draft',
    #         'weekday_price': room.weekday_price,
    #         'weekend_price': room.weekend_price,
    #         'price_weekday_total': weekday_total,
    #         'price_weekend_total': weekend_total,
    #         'total_money': weekday_total + weekend_total,
    #     })
    #
    #     room.state = 'booked'
    #     # request.session['booking_id'] = booking.id
    #     # return request.render('om_hotel.template_booking_confirmation', {
    #     #     'room': room,
    #     #     'check_in_date': check_in_date,
    #     #     'check_out_date': check_out_date,
    #     #     'total_price': weekday_total + weekend_total
    #     # })
    #     return request.render('om_hotel.template_booking_confirmation', {
    #         'room': room,
    #         'check_in_date': check_in_date,
    #         'check_out_date': check_out_date,
    #         'total_price': weekday_total + weekend_total,
    #     })
    #
    # @http.route('/hotel/confirm_booking', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    # def confirm_booking(self, room_id, check_in_date, check_out_date, **kwargs):
    #     room = request.env['hotel.management.room'].sudo().browse(int(room_id))
    #     if not room.exists() or room.state != 'available':
    #         return Response({'error': 'Room is not available'}, status=400)
    #
    #     # Tính giá phòng
    #     check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
    #     check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    #     delta_days = (check_out - check_in).days
    #     weekday_total = 0
    #     weekend_total = 0
    #     for day in range(delta_days):
    #         current_day = check_in + timedelta(days=day)
    #         if current_day.weekday() in [5, 6]:  # Thứ 7, Chủ nhật
    #             weekend_total += room.weekend_price
    #         else:
    #             weekday_total += room.weekday_price
    #     total_price = weekday_total + weekend_total
    #
    #     # Gửi dữ liệu sang trang xác nhận
    #     return request.render('om_hotel.template_booking_review', {
    #         'room': room,
    #         'check_in_date': check_in_date,
    #         'check_out_date': check_out_date,
    #         'total_price': total_price,
    #     })
    #
    # @http.route('/hotel/booking_confirmation', type='http', auth='user', website=True)
    # def booking_confirmation(self, **kwargs):
    #     booking_id = request.session.get('booking_id')
    #     if not booking_id:
    #         return request.redirect('/hotel/available_rooms')
    #
    #     booking = request.env['hotel.management.booking'].sudo().browse(booking_id)
    #     return request.render('om_hotel.template_booking_confirmation', {
    #         'room': booking.room_id,
    #         'check_in_date': booking.check_in_date,
    #         'check_out_date': booking.check_out_date,
    #         'total_price': booking.total_money,
    #     })
    #
    # Hiển thị danh sách dịch vụ
    # @http.route('/hotel/services', type='http', auth="user", website=True)
    # def services(self, **kwargs):
    #     services = request.env['hotel.service.line'].sudo().search([])
    #     return request.render('om_hotel.template_services', {'services': services})
    #
    # # Đặt dịch vụ
    # @http.route('/hotel/order_service', type='http', auth="user", website=True, methods=['POST'])
    # def order_service(self, **kwargs):
    #     service_id = kwargs.get('service_id')
    #     booking = request.env['hotel.management.booking'].sudo().search([
    #         ('customer_id', '=', request.env.user.partner_id.id),
    #         ('state', '=', 'draft')
    #     ], limit=1)
    #     if not booking:
    #         return request.redirect('/hotel/services')
    #     if service_id:
    #         request.env['hotel.service.line'].sudo().create({
    #             'service_id': int(service_id),
    #             'booking_id': booking.id,
    #         })
    #     return request.redirect('/hotel/services')
