from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    x_discount = fields.Float(string='Discount Amount', default=0.0)
    # @api.depends('product_uom_qty', 'discount_amount', 'price_unit', 'tax_id')
    # def _compute_amount(self):
    #     """
    #     Compute the amounts of the SO line.
    #     """
    #     for line in self:
    #         price = line.price_unit - line.discount_amount
    #         taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
    #         line.update({
    #             'price_tax': taxes['total_included'] - taxes['total_excluded'],
    #             'price_total': taxes['total_included'],
    #             'price_subtotal': taxes['total_excluded'],
    #         })

    # @api.depends('product_id', 'product_uom_qty', 'price_unit', 'discount_amount', 'order_id.currency_id')
    # def _compute_amount(self):
    #     for line in self:
    #         discount_price = line.price_unit - line.discount_amount
    #         # Tính subtotal (giá trước thuế)
    #         line.price_subtotal = discount_price * line.product_uom_qty
    #         # Tính toán giá trị thuế và tổng tiền sau thuế
    #         taxes = line.tax_id.compute_all(discount_price, line.order_id.currency_id, line.product_uom_qty,
    #                                         product=line.product_id, partner=line.order_id.partner_id)
    #         line.price_total = taxes['total_included']


    # hàm trong sale.order.line
    # def _prepare_base_line_for_taxes_computation(self, **kwargs):
    #     """ Convert the current record to a dictionary in order to use the generic taxes computation method
    #     defined on account.tax.
    #
    #     :return: A python dictionary.
    #     """
    #     self.ensure_one()
    #     return self.env['account.tax']._prepare_base_line_for_taxes_computation(
    #         self,
    #         **{
    #             'tax_ids': self.tax_id,
    #             'quantity': self.product_uom_qty,
    #             'partner_id': self.order_id.partner_id,
    #             'currency_id': self.order_id.currency_id or self.order_id.company_id.currency_id,
    #             'rate': self.order_id.currency_rate,
    #             **kwargs,
    #         },
    #     )
    #
    # @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    # def _compute_amount(self):
    #     for line in self:
    #         base_line = line._prepare_base_line_for_taxes_computation()
    #         self.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)
    #         line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency']
    #         line.price_total = base_line['tax_details']['raw_total_included_currency']
    #         line.price_tax = line.price_total - line.price_subtotal


    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one() # ensure_one() is a method that ensures that the recordset contains only one record.
        price_unit_discount = self.price_unit - (self.x_discount or 0.0) # discount_amount or 0.0: if discount_amount is False, then 0.0
        if price_unit_discount < 0:
            price_unit_discount = 0
            #Gọi super() để tiếp tục với logic của lớp cha, truyền thêm giá trị price_unit đã điều chỉnh.
        return super()._prepare_base_line_for_taxes_computation(**{
            'price_unit': price_unit_discount,
            **kwargs,
        })


    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'x_discount')
    def _compute_amount(self):
        for line in self:
            # Tính giá trước khi giảm giá
            base_line = line._prepare_base_line_for_taxes_computation()
            self.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id) #Sử dụng _add_tax_details_in_base_line từ account.tax để bổ sung thông tin chi tiết thuế vào dòng dữ liệu cơ sở.
            # discount_price = line.discount_amount or 0.0
            # base_line['tax_details']['raw_total_excluded_currency'] -= discount_price
            line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency'] # Tính giá trị subtotal (giá trước thuế) raw_total_excluded_currency = price_unit_discount × quantity − discount_amount
            line.price_total = base_line['tax_details']['raw_total_included_currency'] # Tính giá trị tổng tiền sau thuế raw_total_included_currency = raw_total_excluded_currency × (1 + tax_rate)
            line.price_tax = line.price_total - line.price_subtotal # Tính giá trị thuế
