from odoo import models, fields

class HotelReportWizard(models.TransientModel):
    _name = 'hotel.report.wizard'
    _description = 'Hotel Report Wizard'

    date_from = fields.Date(string='From Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='To Date', required=True, default=fields.Date.context_today)
    report_type = fields.Selection([
        ('occupancy', 'Room Occupancy'),
        ('revenue', 'Revenue Analysis')
    ], string='Report Type', required=True)

    def action_generate_report(self):
        self.ensure_one()
        if self.report_type == 'occupancy':
            action = self.env.ref('hotel_management.action_hotel_room_occupancy_report')
        else:
            action = self.env.ref('hotel_management.action_hotel_revenue_report')

        action = action.read()[0]
        action['domain'] = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ]
        return action