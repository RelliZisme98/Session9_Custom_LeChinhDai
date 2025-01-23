from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    booking_id = fields.Many2one('hotel.management.booking', string='Hotel Booking')

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        for order in self:
            if order.booking_id:
                # Create service lines in the booking
                for line in order.lines:
                    self.env['hotel.service'].create({
                        'booking_id': order.hotel_booking_id.id,
                        'product_id': line.product_id.id,
                        'quantity': line.qty,
                        'unit_price': line.price_unit,
                    })
        return res


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_hotel_booking(self):
        return {
            'search_params': {
                'domain': [('state', '=', 'checked_in')],
                'fields': ['name', 'partner_id', 'room_id', 'total_amount'],
            }
        }

    def _get_pos_ui_hotel_booking(self, params):
        return self.env['hotel.management.booking'].search_read(**params['search_params'])
