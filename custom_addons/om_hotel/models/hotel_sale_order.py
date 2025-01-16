from odoo import models, api, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    booking_id = fields.One2many('hotel.management.booking', 'sale_order_id', string="Related Bookings")
    @api.model
    def write(self, vals):
        # Ghi đè logic ghi dữ liệu trong Sale Order
        result = super(SaleOrder, self).write(vals)

        # Tìm các booking liên quan
        for order in self:
            if order.booking_id:  # booking_ids là quan hệ Many2one hoặc One2many từ Sale Order tới Booking
                for booking in order.booking_id:
                    # Cập nhật thông tin cần đồng bộ
                    if 'order_line' in vals:  # Nếu có thay đổi trong dòng đơn hàng
                        total_service_price = sum(line.price_subtotal for line in order.order_line)
                        booking.write({
                            'service_total': total_service_price,
                            'total_money': order.amount_total,
                        })

        return result
