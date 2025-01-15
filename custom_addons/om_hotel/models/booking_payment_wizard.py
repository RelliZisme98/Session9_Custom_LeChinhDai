from odoo import models, fields, api
from odoo.exceptions import ValidationError

class BookingPaymentWizard(models.TransientModel):
    _name = 'booking.payment.wizard'
    _description = 'Booking Payment Wizard'

    booking_id = fields.Many2one('hotel.management.booking', string='Booking', required=True)
    hotel_id = fields.Many2one(related='booking_id.hotel_id', string='Hotel', readonly=True)
    room_id = fields.Many2one(related='booking_id.room_id', string='Room', readonly=True)
    payment_amount = fields.Float(string='Số tiền thanh toán', required=True)
    total_money = fields.Float(string='Total Money', readonly=True)

    @api.model
    def default_get(self, fields):
        res = super(BookingPaymentWizard, self).default_get(fields)
        # Set the default payment_amount to the total money of the booking
        booking_id = self.env.context.get('active_id')
        if booking_id:
            booking = self.env['hotel.management.booking'].browse(booking_id)
            if booking:
                res.update({
                    'booking_id': booking.id,
                    'payment_amount': booking.total_money,  # Automatically set the payment_amount
                    'total_money': booking.total_money,     # Display total_money
                })
        return res
    @api.constrains('payment_amount')
    def _check_payment_amount(self):
        for record in self:
            if record.payment_amount <= 0:
                raise ValidationError('Số tiền thanh toán phải lớn hơn 0.')

    def action_confirm_payment(self):
        self.ensure_one()
        if self.payment_amount != self.booking_id.total_money:
            raise ValidationError("The payment amount must match the total amount!")
        self.booking_id.write({
            'payment_status': 'paid',
            'payment_date': fields.Datetime.now(),
            'payment_amount': self.payment_amount,
        })
        return {'type': 'ir.actions.act_window_close'}