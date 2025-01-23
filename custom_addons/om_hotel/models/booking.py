from odoo import models, fields, api
from datetime import date, datetime, timedelta
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError
from odoo import exceptions


class Booking(models.Model):
    _name = 'hotel.management.booking'
    _description = 'Booking Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one('res.company', string='Company')
    name = fields.Char(string='Booking Reference', required=True, default=lambda self: self.env['ir.sequence'].next_by_code('booking.sequence'))
    customer_name = fields.Char(string='Customer Name', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer')  # Liên kết đến res.partner
    booking_date = fields.Date(string='Booking Date', default=fields.Date.today)
    hotel_id = fields.Many2one('hotel.management.hotel', string='Hotel', required=True)
    room_type = fields.Selection([('single', 'Single Bed'),
                                        ('double', 'Double Bed')],
                                         string='Room Type',
                                        required=True)
    room_id = fields.Many2one('hotel.management.room',
                              string='Room',
                              domain="[('hotel_id', '=', hotel_id), ('bed_type', '=', room_type), ('state', '=', 'available')]",
                              required=True)
    weekday_price = fields.Float(related='room_id.weekday_price', string='Weekday Price', readonly=True)
    weekend_price = fields.Float(related='room_id.weekend_price', string='Weekend Price', readonly=True)
    check_in_date = fields.Date(string='Check-in Date', required=True)
    check_out_date = fields.Date(string='Check-out Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')], string='Booking Status', default='draft')
    # New fields
    payment_status = fields.Selection([('unpaid', 'Chưa thanh toán'), ('paid', 'Đã thanh toán')],string='Loại thanh toán', default='unpaid', readonly=True)
    payment_date = fields.Datetime(string='Ngày thanh toán', readonly=True)
    payment_amount = fields.Float(string='Số tiền thanh toán', readonly=True)

    # new field
    number_of_nights = fields.Integer(string='Number of Nights', compute='_compute_number_of_nights') # Tính số đêm ở
    # room_price = fields.Float(related='room_id.price', string='Room Price', readonly=True) # Giá phòng
    service_ids = fields.One2many('hotel.service.line', 'booking_id', string='Services Used') # Dịch vụ
    service_total = fields.Float(string='Service Total', compute='_compute_service_total') # Tổng tiền dịch vụ
    total_money = fields.Float(string='Total Money', compute='_compute_total_money') # Tổng tiền
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True) # Đơn đặt hàng
    price_weekday_total = fields.Float(string='Weekday Price Total',
                                       compute='_compute_price_total')  # Tổng tiền ngày trong tuần
    price_weekend_total = fields.Float(string='Weekend Price Total',
                                       compute='_compute_price_total')  # Tổng tiền ngày cuối tuần
    # product_id = fields.Many2one(
    #     'product.product',
    #     string='Booking Product',
    #     domain=[('product_type', '=', 'booking')],  # Chỉ hiển thị sản phẩm loại booking
    #     required=True
    # )
    currency_id = fields.Many2one('res.currency', string='Currency', related='service_ids.currency_id', store=True)
    @api.depends('check_in_date', 'check_out_date')
    def _compute_number_of_nights(self):
        for record in self:
            if record.check_in_date and record.check_out_date:
                date_start = fields.Date.from_string(record.check_in_date)
                date_end = fields.Date.from_string(record.check_out_date)
                record.number_of_nights = (date_end - date_start).days
            else:
                record.number_of_nights = 0

    # # Tính tổng tiền dịch vụ:
    # @api.depends('service_ids.price_total')
    # def _compute_service_total(self):
    #     for record in self:
    #         record.service_total = sum(service.price_total for service in record.service_ids)
    @api.depends('service_ids.price_total')  # Sử dụng service_ids.total_amount
    def _compute_service_total(self):
        for booking in self:
            booking.service_total = sum(service.price_total for service in booking.service_ids)

    # Tính tổng tiền:
    @api.depends('room_id', 'number_of_nights', 'check_in_date', 'service_total')
    def _compute_total_money(self):
        for record in self:
            if record.room_id and record.check_in_date and record.number_of_nights:
                # Lấy giá phòng theo ngày trong tuần và cuối tuần
                weekday_price = record.room_id.weekday_price
                weekend_price = record.room_id.weekend_price

                # Tính tổng tiền dựa trên ngày check-in và check-out
                total_room_price = 0
                date_start = fields.Date.from_string(record.check_in_date)
                for i in range(record.number_of_nights):
                    day = date_start + timedelta(days=i)
                    if day.weekday() < 5:  # Monday to Friday
                        total_room_price += weekday_price
                        record.price_weekday_total += weekday_price
                    else:  # Saturday and Sunday
                        total_room_price += weekend_price
                        record.price_weekend_total += weekend_price

                # Tính tổng tiền với dịch vụ và thuế
                total_without_tax = total_room_price + record.service_total

                # Nếu có thông tin từ sale_order_id, tính thêm thuế
                if record.sale_order_id:
                    tax_amount = sum(
                        line.tax_id.amount * line.price_subtotal / 100 for line in record.sale_order_id.order_line if
                        line.tax_id
                    )
                    record.total_money = total_without_tax + tax_amount
                else:
                    record.total_money = total_without_tax
            else:
                    record.total_money = 0
    # tien phong cuoi tuan va ngay thuong
    @api.depends('number_of_nights', 'room_id', 'check_in_date')
    def _compute_total_amount(self):
        for record in self:
            if record.room_id and record.number_of_nights and record.check_in_date:
                weekday_price = record.room_id.price_weekday
                weekend_price = record.room_id.price_weekend
                total = 0
                # Tính tổng tiền cho số đêm lưu trú
                date_start = fields.Date.from_string(record.check_in_date)
                for i in range(record.number_of_nights):
                    day = date_start + timedelta(days=i)
                    # Kiểm tra xem ngày là ngày trong tuần hay cuối tuần
                    if day.weekday() < 5:  # Monday to Friday
                        total += weekday_price
                    else:  # Saturday and Sunday
                        total += weekend_price

                record.total_amount = total

    @api.depends('room_id.weekday_price', 'room_id.weekend_price', 'number_of_nights', 'check_in_date')
    def _compute_price_total(self):
        for record in self:
            # Tính tổng giá cho ngày trong tuần và cuối tuần
            weekday_price = record.room_id.weekday_price
            weekend_price = record.room_id.weekend_price
            total_weekday = 0
            total_weekend = 0
            if record.room_id and record.number_of_nights and record.check_in_date:
                date_start = fields.Date.from_string(record.check_in_date)
                for i in range(record.number_of_nights):
                    day = date_start + timedelta(days=i)
                    if day.weekday() < 5:  # Monday to Friday
                        total_weekday += weekday_price
                    else:  # Saturday and Sunday
                        total_weekend += weekend_price

            record.price_weekday_total = total_weekday
            record.price_weekend_total = total_weekend

    def get_room_price(self):
        if self.room_id:
            return self.room_id.weekday_price if fields.Date.today().weekday() < 5 else self.room_id.weekend_price
        return 0.0
    @api.model
    def write(self, vals):
        result = super(Booking, self).write(vals)

        # Nếu có thay đổi trong service_ids
        if 'service_ids' in vals:
            for record in self:
                if record.sale_order_id:
                    sale_order = record.sale_order_id

                    # Cập nhật các dòng dịch vụ trong sale.order.line
                    for service in record.service_ids:
                        # Lấy hoặc tạo dòng bán hàng tương ứng
                        order_line = sale_order.order_line.filtered(
                            lambda l: l.product_id == service.product_id
                        )

                        if order_line:
                            # Nếu dòng bán hàng đã tồn tại, cập nhật lại giá và tên
                            order_line.write({
                                'price_unit': service.price_total,  # Giá từ dịch vụ
                                'name': service.name or 'Service: ' + service.product_id.name,
                            })
                        else:
                            # Nếu dòng bán hàng chưa tồn tại, tạo dòng mới
                            self.env['sale.order.line'].create({
                                'order_id': sale_order.id,
                                'product_id': service.product_id.id,
                                'product_uom_qty': service.quantity,
                                'price_unit': service.price_total,
                                'name': service.name or 'Service: ' + service.product_id.name,
                            })

                    # Tự động cập nhật lại tổng tiền (amount_total)
                    sale_order.amount_total = record.total_money

                # Cập nhật lại tổng tiền trong booking nếu cần
                record._compute_total_money()

        return result




    # Tạo đơn hàng bán
    def action_create_sale_order(self):
        self.ensure_one()
        partner = self.env['res.partner'].search([('name', '=', self.customer_name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({'name': self.customer_name})
        self.customer_id = partner.id  # Liên kết đối tác với booking

        # Kiểm tra số đêm và giá phòng
        if not self.number_of_nights or self.number_of_nights <= 0:
            raise ValidationError("Number of nights must be greater than zero.")

        # Lấy giá phòng từ price_weekday hoặc price_weekend
        room_price = self.room_id.weekday_price if fields.Date.today().weekday() < 5 else self.room_id.weekend_price
        if not room_price or room_price <= 0:
            raise ValidationError(f"Room price for {self.room_id.name} is invalid.")

        # Tìm hoặc tạo sản phẩm "Room Booking"
        product_name = f'Room booking for {self.number_of_nights} nights'
        room_booking_product = self.env['product.product'].search([('name', '=', product_name)], limit=1)

        if not room_booking_product:
            room_booking_product = self.env['product.product'].create({
                'name': product_name,
                'type': 'service',
                'lst_price': room_price,
                'uom_id': self.env.ref('uom.product_uom_day').id,  # Đơn vị đo là "Ngày"
            })

        # Chuẩn bị các dòng bán hàng
        order_line_vals = []

        # Dịch vụ bổ sung
        for service in self.service_ids:
            if not service.product_id:
                service_product = self.env['product.product'].search([('name', '=', service.name)], limit=1)
                if not service_product:
                    service_product = self.env['product.product'].create({
                        'name': service.name,
                        'type': 'service',
                        'lst_price': service.price_total,
                    })
                    service.product_id = service_product
            else:
                service_product = service.product_id

            order_line_vals.append((0, 0, {
                'name': service.name,
                'product_uom_qty': 1,
                # 'price_unit': service.price,
                'price_unit': service.price_total,
                'product_id': service_product.id,
            }))

        # Dòng đặt phòng
        order_line_vals.append((0, 0, {
            'name': product_name,
            'product_uom_qty': self.number_of_nights,
            'price_unit': room_price,
            'product_id': room_booking_product.id,  # Liên kết với sản phẩm "Room Booking"
        }))

        # Tạo đơn bán hàng
        sale_order_vals = {
            'partner_id': self.customer_id.id,
            'order_line': order_line_vals,
        }
        sale_order = self.env['sale.order'].create(sale_order_vals)
        self.sale_order_id = sale_order.id
        self.total_money = sale_order.amount_total

        # Kiểm tra và cập nhật trạng thái thanh toán khi đơn hàng được xác nhận
        if sale_order.state == 'sale' and self.payment_amount and self.payment_amount >= self.total_money:
            self.payment_status = 'paid'
            self.payment_date = fields.Datetime.now()

        # Tạo lịch sử đặt phòng
        # for record in self:
        #     sale_order = self.env['sale.order'].create({
        #         'partner_id': record.customer_id.id,
        #         'order_line': [(0, 0, {
        #             'product_id': record.room_id.product_id.id,
        #             'product_uom_qty': record.number_of_nights,
        #             # 'price_unit': record.room_id.price,
        #             'price_unit': room_price,
        #         })]
        #     })
        #     for service in record.service_ids:
        #         sale_order.order_line.create({
        #             'order_id': sale_order.id,
        #             'product_id': service.product_id.id,
        #             'product_uom_qty': service.quantity,
        #             'price_unit': service.unit_price,
        #         })
        #     record.sale_order_id = sale_order.id
        return sale_order

    # Phương thức xử lý xác nhận booking:
    @api.model
    def action_approve(self):
        """
        Chuyển trạng thái của booking từ 'draft' sang 'confirmed'.
        Chỉ áp dụng cho các bản ghi có trạng thái hiện tại là 'draft'.
        """
        draft_records = self.filtered(lambda r: r.state == 'draft')
        draft_records.write({'state': 'confirmed'})

    # Đảm bảo ngày check-in phải trước ngày check-out:
    @api.constrains('check_in_date', 'check_out_date')
    def _check_dates(self):
        for record in self:
            if record.check_in_date > record.check_out_date:
                raise ValidationError('Check-out date must be after check-in date!')



    # đảm bảo không đặt phòng đã được đặt trong khoảng thời gian khác:
    @api.constrains('check_in_date', 'check_out_date', 'room_id')
    def _check_room_availability(self):
        for record in self:
            overlapping_bookings = self.env['hotel.management.booking'].search([
                ('room_id', '=', record.room_id.id),
                ('state', '=', 'confirmed'),
                ('check_in_date', '<', record.check_out_date),
                ('check_out_date', '>', record.check_in_date),
                ('id', '!=', record.id),
            ])
            if overlapping_bookings:
                raise exceptions.ValidationError(
                    f"Room {record.room_id.name} is already booked for the selected dates."
                )


    # ensures the validity of the booking dates
    @api.constrains('check_in_date', 'check_out_date')
    def _check_dates(self):
        for record in self:
            if record.check_in_date > record.check_out_date:
                raise ValidationError('Check-out date must be after check-in date!')
            if record.check_in_date < fields.Date.today():
                raise ValidationError('Check-in date cannot be in the past!')
            if record.check_out_date < fields.Date.today():
                raise ValidationError('Check-out date cannot be in the past!')



    # Không cho phép đặt phòng nếu trạng thái phòng không phải là 'available':
    @api.constrains('room_id')
    def _check_room_state(self):
        for record in self:
            if record.room_id.state != 'available':
                raise ValidationError(
                    f"Room {record.room_id.name} is not available for booking."
                )


 # Đảm bảo không đặt phòng đang bảo trì:
    @api.model
    def create(self, vals):
        room = self.env['hotel.management.room'].browse(vals.get('room_id'))
        if room.state == 'maintenance':
            raise ValidationError(f"Room {room.name} is under maintenance and cannot be booked.")
        return super(Booking, self).create(vals)



    @api.depends('sale_order_id.invoice_ids.state', 'sale_order_id.invoice_ids.payment_state')
    def _compute_payment_status_from_invoice(self):
        for record in self:
            # Kiểm tra trạng thái của hóa đơn liên kết với sale order
            if record.sale_order_id:
                # Lặp qua tất cả hóa đơn trong sale order
                for invoice in record.sale_order_id.invoice_ids:
                    # Kiểm tra nếu hóa đơn đã được thanh toán
                    if invoice.state == 'posted' and invoice.payment_state == 'paid':
                        record.payment_status = 'paid'
                        record.payment_date = fields.Datetime.now()  # Cập nhật ngày thanh toán
                        break  # Nếu có hóa đơn đã thanh toán thì không cần kiểm tra tiếp
                    else:
                        record.payment_status = 'unpaid'  # Nếu chưa thanh toán
                        record.payment_date = False
            else:
                record.payment_status = 'unpaid'  # Nếu không có sale order thì đánh dấu là chưa thanh toán
                record.payment_date = False

    # Phương thức xử lý xác nhận booking:
    def confirm_booking(self):
        for record in self:
            _logger.info('Booking confirmed: %s by user %s', record.name, self.env.user.name)
            record.state = 'confirmed'
            record.room_id.state = 'booked'

            # Tạo lịch sử đặt phòng
            self.env['hotel.management.booking'].create({
                'customer_id': record.customer_name,
                'hotel_id': record.hotel_id.id,
                'room_id': record.room_id.id,
                'check_in_date': record.check_in_date,
                'check_out_date': record.check_out_date,
                'state': 'confirmed',
            })

            # Kiểm tra và cập nhật trạng thái thanh toán nếu tổng tiền và tiền thanh toán bằng nhau
            if record.payment_amount and record.payment_amount >= record.total_money:
                record.payment_status = 'paid'
                record.payment_date = fields.Datetime.now()  # Cập nhật ngày thanh toán nếu đã thanh toán đầy đủ

    def cancel_booking(self):
        for record in self:
            _logger.info('Booking cancelled: %s by user %s', record.name, self.env.user.name)
            record.state = 'cancelled'
            record.room_id.state = 'available'

    # Mở popup thanh toán:
    def action_pay(self):

        if self.payment_status == 'paid':
            raise ValidationError("This booking has already been paid.")

        if not self.total_money:
            raise ValidationError("Total money cannot be zero.")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'booking.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_booking_id': self.id,
                        'default_total_money': self.total_money}, # Gửi tổng tiền sang wizard
                         }