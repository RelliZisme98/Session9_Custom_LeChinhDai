from odoo import models, fields

class HotelService(models.Model):
    _name = 'hotel.service'
    _description = 'Hotel Service'

    name = fields.Char(string='Service Name', required=True)
    price = fields.Float(string='Price', required=True)
    service_type = fields.Selection([
        ('food', 'Food'),
        ('laundry', 'Laundry'),
        ('spa', 'Spa'),
        ('other', 'Other')
    ], string='Service Type', required=True)
    booking_id = fields.Many2one('hotel.management.booking', string='Booking')
    product_id = fields.Many2one('product.product', string='Product', required=True)