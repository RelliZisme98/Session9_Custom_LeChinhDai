from odoo import models, fields, api
from odoo.api import ondelete
from odoo.exceptions import UserError


class HotelServiceLine(models.Model):
    _name = 'hotel.service.line'
    _description = 'Hotel Service Line'

    service_id = fields.Many2one('hotel.service', string='Service', required=True, ondelete='cascade')
    # booking_id = fields.Many2one('hotel.management.booking', string='Booking', required=True)
    # product_type = fields.Selection([
    #     ('service', 'Service'),
    #     ('product', 'Product')
    # ], string="Service/Product Type", default='service', required=True)
    booking_id = fields.Many2one('hotel.management.booking', string='Booking', required=True, ondelete ='cascade')
    # product_id = fields.Many2one('product.product', string='Product/Service', required=True)
    product_id = fields.Many2one('product.product', string="Product", required=True,
                                 default=lambda self: self._get_default_product())
    name = fields.Char(related='product_id.name', string='Description')
    quantity = fields.Float(string='Quantity', default=1.0, help="Only for products that require quantity", required=True)
    unit_price = fields.Float(string='Unit Price', compute='_compute_unit_price', store=True)
    price_total = fields.Float(string='Total Price', compute='_compute_price_total', store=True)
    stock_move_id = fields.Many2one('stock.move', string='Stock Move')
    currency_id = fields.Many2one('res.currency', string='Currency', related='service_id.currency_id', store=True)
    product_qty_available = fields.Float(related='product_id.qty_available', string='Stock Available', readonly=True)

    @api.depends('product_id')
    def _compute_qty_available(self):
        for line in self:
            if line.product_id:
                line.product_qty_available = line.product_id.qty_available
            else:
                line.product_qty_available = 0.0
    @api.depends('product_id')
    def _compute_unit_price(self):
        for line in self:
            # Lấy giá sản phẩm từ inventory
            if line.product_id:
                line.unit_price = line.product_id.lst_price  # Giá bán lẻ (list price)

    @api.onchange('quantity', 'product_id')
    def _check_stock_available_and_update(self):
        for record in self:
            if record.product_id:
                # Kiểm tra tồn kho sản phẩm
                if record.product_id.qty_available < record.quantity:
                    raise UserError(("Không đủ số lượng trong kho để thực hiện dịch vụ này!"))

                # Cập nhật số lượng tồn kho sau khi người dùng thay đổi
                record.product_id.write({
                    'qty_available': record.product_id.qty_available - record.quantity
                })

    def add_stock_move(self, product_id, quantity):
        """
        Hàm này dùng để nhập sản phẩm vào kho.
        """
        stock_move_obj = self.env['stock.move']

        # Tạo một chuyển động kho (Nhập kho)
        stock_move = stock_move_obj.create({
            'name': 'Import stock for product %s' % product_id.name,
            'product_id': product_id.id,
            'product_uom_qty': quantity,
            'product_uom': product_id.uom_id.id,  # Đơn vị tính sản phẩm
            'location_id': self.env.ref('stock.stock_location_supplier').id,  # Vị trí kho (từ nhà cung cấp)
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,  # Vị trí kho (đến kho)
            'state': 'draft',  # Trạng thái khởi tạo
        })

        stock_move.action_confirm()  # Xác nhận chuyển động kho
        stock_move.action_done()  # Hoàn thành chuyển động kho

        # Cập nhật số lượng tồn kho sau khi nhập kho
        product = self.env['product.product'].browse(product_id.id)
        new_qty = product.qty_available + quantity
        product.write({'qty_available': new_qty})

        return stock_move

    def add_to_stock(self, quantity):
        """
        Hàm này dùng để bổ sung số lượng vào kho.
        """
        for record in self:
            if record.product_id:
                stock_move = self.add_stock_move(record.product_id, quantity)
                # Cập nhật lại số lượng tồn kho của dòng dịch vụ
                record.product_qty_available = record.product_id.qty_available
    @api.depends('quantity', 'unit_price')
    def _compute_price_total(self):
        for line in self:
            line.price_total = line.quantity * line.unit_price

    def _get_default_product(self):
        # Lấy sản phẩm mặc định dựa trên loại dịch vụ
        return self.env['product.product'].search([('name', '=', 'Default Product')], limit=1)

    @api.model
    def create(self, vals):
        product = self.env['product.product'].browse(vals.get('product_id'))
        qty_available = product.qty_available

        if qty_available < vals.get('quantity', 0):
            raise UserError('Không đủ số lượng trong kho để tạo dịch vụ này.')

        # Cập nhật tồn kho sau khi tạo dòng dịch vụ
        product.write({
            'qty_available': qty_available - vals.get('quantity', 0),
        })

        return super(HotelServiceLine, self).create(vals)

    def write(self, vals):
        if 'quantity' in vals:
            for line in self:
                product = line.product_id
                old_qty = line.quantity
                new_qty = vals['quantity']

                if old_qty != new_qty:
                    qty_available = product.qty_available
                    # Cập nhật tồn kho khi số lượng thay đổi
                    product.write({
                        'qty_available': qty_available + old_qty - new_qty,
                    })

        return super(HotelServiceLine, self).write(vals)


