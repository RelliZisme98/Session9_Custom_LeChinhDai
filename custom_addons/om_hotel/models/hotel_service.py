from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HotelService(models.Model):
    _name = 'hotel.service'
    _description = 'Hotel Service and Product Usage'

    name = fields.Char(string='Service Reference', required=True, default='New')
    product_id = fields.Many2one('product.product', string="Product", required=True)
    booking_id = fields.Many2one('hotel.management.booking', string='Booking', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', related='booking_id.customer_id', store=True)
    room_id = fields.Many2one('hotel.management.room', string='Room', related='booking_id.room_id', store=True)
    service_line_ids = fields.One2many('hotel.service.line', 'service_id', string='Service Lines')
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_total_amount', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True)

    @api.depends('service_line_ids.price_total')
    def _compute_total_amount(self):
        for service in self:
            service.total_amount = sum(line.price_total for line in service.service_line_ids)

    def action_confirm(self):
        for service in self:
            if not service.service_line_ids:
                raise UserError(_("You must add at least one service or product."))
            service._update_inventory()
            service.state = 'confirmed'

    def action_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def _update_inventory(self):
        """ Deduct inventory based on product usage, checking if stock is available """
        for line in self.service_line_ids:
            if line.product_id.type in ['consu', 'product'] and line.quantity > 0:
                available_qty = line.product_id.with_company(self.env.company).qty_available
                if available_qty < line.quantity:
                    raise UserError(_("Not enough stock for product %s. Available: %s, Required: %s") % (
                        line.product_id.display_name, available_qty, line.quantity))
                line.product_id.sudo()._update_quantity_on_hand(-line.quantity)



    def create_sale_order(self):
        for service in self:
            # Tạo các dòng đơn hàng từ các dòng dịch vụ
            order_lines = []
            for line in service.service_line_ids:
                order_line = {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'price_unit': line.unit_price,
                    'name': line.product_id.name,
                    'tax_id': [(6, 0, [tax.id for tax in line.product_id.taxes_id])],  # Đảm bảo thuế đi kèm
                }
                order_lines.append((0, 0, order_line))

            # Tạo đơn hàng bán
            order_vals = {
                'partner_id': service.customer_id.id,
                'order_line': order_lines,
                'origin': service.name,  # Gắn nguồn từ dịch vụ
            }
            sale_order = self.env['sale.order'].create(order_vals)
            service.booking_id.sale_order_id = sale_order
