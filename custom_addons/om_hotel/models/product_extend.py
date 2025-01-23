from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    # product_type = fields.Selection([
    #     ('booking', 'Booking Product'),
    #     ('service', 'Service/Product')
    # ], string="Product Type", default='service')
    def _update_quantity_on_hand(self, quantity_change):
        """Update inventory for a product."""
        for product in self:
            product.with_context(inventory_mode=True).write({
                'qty_available': product.qty_available + quantity_change
            })