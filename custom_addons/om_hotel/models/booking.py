from odoo import models, fields, api
from datetime import date
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError
from odoo import exceptions


class Booking(models.Model):
    _name = 'hotel.management.booking'
    _description = 'Booking Management'

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
    room_price = fields.Float(related='room_id.price', string='Room Price', readonly=True) # Giá phòng
    service_ids = fields.One2many('hotel.service', 'booking_id', string='Services') # Dịch vụ
    service_total = fields.Float(string='Service Total', compute='_compute_service_total') # Tổng tiền dịch vụ
    total_money = fields.Float(string='Total Money', compute='_compute_total_money') # Tổng tiền
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True) # Đơn đặt hàng

    # Tính số đêm ở:
    @api.depends('check_in_date', 'check_out_date')
    def _compute_number_of_nights(self):
        for record in self:
            if not record.check_in_date or not record.check_out_date:
                _logger.error(f"Missing check-in or check-out for booking ID {record.id}")
                record.number_of_nights = 0
            else:
                try:
                    record.number_of_nights = (record.check_out_date - record.check_in_date).days
                except Exception as e:
                    _logger.error(f"Error computing number of nights for booking ID {record.id}: {e}")
                    record.number_of_nights = 0
    # Tính tổng tiền dịch vụ:
    @api.depends('service_ids.price')
    def _compute_service_total(self):
        for record in self:
            record.service_total = sum(service.price for service in record.service_ids)


   # Tính tổng tiền:
    @api.depends('room_price', 'number_of_nights', 'service_total', 'sale_order_id')
    def _compute_total_money(self):
        for record in self:
            # Tính tổng tiền phòng và dịch vụ
            total_without_tax = (record.room_price * record.number_of_nights) + record.service_total

            # Nếu có sale_order_id, lấy thông tin thuế từ sale.order
            if record.sale_order_id:
                # Tổng thuế từ đơn hàng
                tax_amount = sum(
                    line.tax_id.amount * line.price_subtotal / 100 for line in record.sale_order_id.order_line if
                    line.tax_id)
                # Cập nhật tổng tiền bao gồm thuế
                record.total_money = total_without_tax + tax_amount
            else:
                # Nếu không có sale_order, chỉ tính tiền phòng và dịch vụ
                record.total_money = total_without_tax

    # Tạo hóa đơn từ đơn hàng:
    @api.model
    def write(self, vals):
        result = super(Booking, self).write(vals)

        # Nếu dịch vụ được thêm mới, cập nhật sale order
        if 'service_ids' in vals:
            for record in self:
                if record.sale_order_id:
                    # Cập nhật lại các dòng bán hàng trong sale.order
                    sale_order = record.sale_order_id
                    # Cập nhật các dòng dịch vụ trong đơn hàng
                    for service in record.service_ids:
                        # Kiểm tra nếu sản phẩm dịch vụ đã tồn tại trong đơn hàng
                        order_line = sale_order.order_line.filtered(lambda l: l.product_id == service.product_id)
                        if order_line:
                            # Cập nhật dòng dịch vụ đã có
                            order_line.price_unit = service.price
                            order_line.name = service.name  # Đảm bảo mô tả dòng dịch vụ được cập nhật
                        else:
                            # Nếu chưa có, tạo dòng bán hàng mới cho dịch vụ
                            sale_order.order_line.create({
                                'order_id': sale_order.id,
                                'product_id': service.product_id.id,
                                'product_uom_qty': 1,
                                'price_unit': service.price,
                                'name': service.name or 'Service: ' + service.name,  # Đảm bảo mô tả không bị trống
                            })
                    # Cập nhật lại tổng tiền trong đơn hàng (total_money)
                    sale_order.amount_total = record.total_money
                    # sale_order.recompute_prices() # Cập nhật lại tổng tiền trong đơn hàng
                    record._compute_total_money()  # Ensure total_money is updated in booking
        return result

    def action_create_sale_order(self):
        self.ensure_one()
        # Tự động tạo đối tác nếu chưa có trong res.partner
        partner = self.env['res.partner'].search([('name', '=', self.customer_name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': self.customer_name,
            })
        self.customer_id = partner.id  # Liên kết đối tác với booking

        # Kiểm tra số đêm và giá phòng
        if not self.number_of_nights or self.number_of_nights <= 0:
            raise ValidationError("Number of nights must be greater than zero.")
        if not self.room_price or self.room_price <= 0:
            raise ValidationError(f"Room price for {self.room_id.name} is invalid.")

        # Tìm hoặc tạo sản phẩm "Room Booking"
        product_name = f'Room booking for {self.number_of_nights} nights'
        room_booking_product = self.env['product.product'].search([('name', '=', product_name)], limit=1)

        if not room_booking_product:
            room_booking_product = self.env['product.product'].create({
                'name': product_name,
                'type': 'service',  # Loại sản phẩm là dịch vụ
                'lst_price': self.room_price,  # Giá phòng mỗi đêm
                'uom_id': self.env.ref('uom.product_uom_day').id,  # Đơn vị đo là "Ngày"
            })

        # Chuẩn bị các dòng bán hàng
        order_line_vals = []

        # Dịch vụ bổ sung
        for service in self.service_ids:
            # Kiểm tra hoặc tạo sản phẩm cho mỗi dịch vụ
            if not service.product_id:
                service_product = self.env['product.product'].search([('name', '=', service.name)], limit=1)
                if not service_product:
                    service_product = self.env['product.product'].create({
                        'name': service.name,
                        'type': 'service',  # Loại sản phẩm là dịch vụ
                        'lst_price': service.price,  # Giá dịch vụ
                    })
                    service.product_id = service_product  # Liên kết dịch vụ với sản phẩm
            else:
                service_product = service.product_id

            # Thêm dịch vụ vào dòng bán hàng
            order_line_vals.append((0, 0, {
                'name': service.name,
                'product_uom_qty': 1,
                'price_unit': service.price,
                'product_id': service_product.id,
            }))

        # Dòng đặt phòng
        order_line_vals.append((0, 0, {
            'name': product_name,
            'product_uom_qty': self.number_of_nights,
            'price_unit': self.room_price,
            'product_id': room_booking_product.id,  # Liên kết với sản phẩm "Room Booking"
        }))

        # Tạo đơn bán hàng
        sale_order_vals = {
            'partner_id': self.customer_id.id,  # Liên kết với khách hàng
            'order_line': order_line_vals,  # Các dòng đơn hàng
        }
        sale_order = self.env['sale.order'].create(sale_order_vals)
        self.sale_order_id = sale_order.id
        # Cập nhật lại total_money trong booking từ sale_order
        self.total_money = sale_order.amount_total
        # Kiểm tra và cập nhật trạng thái thanh toán khi đơn hàng được xác nhận
        if sale_order.state == 'sale' and self.payment_amount and self.payment_amount >= self.total_money:
            self.payment_status = 'paid'
            self.payment_date = fields.Datetime.now()  # Cập nhật ngày thanh toán

        return sale_order

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