# from odoo import models, fields, api, tools
# from datetime import datetime, timedelta
#
# class HotelRoomOccupancyReport(models.Model):
#     _name = 'hotel.room.occupancy.report'
#     _description = 'Room Occupancy Analysis'
#     _auto = False
#
#     date = fields.Date(string='Date', readonly=True)
#     room_id = fields.Many2one('hotel.management.room', string='Room', readonly=True)
#     room_type = fields.Selection(related='room_id.bed_type', string='Room Type', readonly=True)
#     state = fields.Selection([
#         ('occupied', 'Occupied'),
#         ('available', 'Available'),
#         ('maintenance', 'Maintenance')
#     ], string='Status', readonly=True)
#     booking_id = fields.Many2one('hotel.management.booking', string='Booking', readonly=True)
#     partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
#     revenue = fields.Float(string='Revenue', readonly=True)
#
#     def init(self):
#         tools.drop_view_if_exists(self.env.cr, self._table)
#         self.env.cr.execute("""
#             CREATE or REPLACE VIEW %s as (
#                 WITH RECURSIVE dates AS (
#                     SELECT DATE(MIN(check_in_date)) AS date
#                     FROM hotel_management_booking
#                     UNION ALL
#                     SELECT date + 1
#                     FROM dates
#                     WHERE date < CURRENT_DATE
#                 )
#                 SELECT
#                     row_number() OVER () as id,
#                     d.date as date,
#                     r.id as room_id,
#                     CASE
#                         WHEN b.id IS NOT NULL THEN 'occupied'
#                         WHEN r.state = 'maintenance' THEN 'maintenance'
#                         ELSE 'available'
#                     END as state,
#                     b.id as booking_id,
#                     b.partner_id as partner_id,
#                     CASE
#                         WHEN EXTRACT(DOW FROM d.date) IN (0, 6) THEN r.weekend_price
#                         ELSE r.weekday_price
#                     END as revenue
#                 FROM dates d
#                 CROSS JOIN hotel_management_room r
#                 LEFT JOIN hotel_management_booking b ON b.room_id = r.id
#                     AND d.date >= b.check_in_date
#                     AND d.date < b.check_out_date
#                     AND b.state IN ('confirmed', 'checked_in')
#             )
#         """ % self._table)
#
# class HotelRevenueReport(models.Model):
#     _name = 'hotel.revenue.report'
#     _description = 'Revenue Analysis'
#     _auto = False
#
#     date = fields.Date(string='Date', readonly=True)
#     room_id = fields.Many2one('hotel.management.room', string='Room', readonly=True)
#     room_type = fields.Selection(related='room_id.bed_type', string='Room Type', readonly=True)
#     booking_id = fields.Many2one('hotel.management.booking', string='Booking', readonly=True)
#     partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
#     room_revenue = fields.Float(string='Room Revenue', readonly=True)
#     service_revenue = fields.Float(string='Service Revenue', readonly=True)
#     total_revenue = fields.Float(string='Total Revenue', readonly=True)
#
#     def init(self):
#         tools.drop_view_if_exists(self.env.cr, self._table)
#         self.env.cr.execute("""
#             CREATE or REPLACE VIEW %s as (
#                 WITH booking_services AS (
#                     SELECT
#                         b.id as booking_id,
#                         sum(sl.price_total) as service_total
#                     FROM hotel_management_booking b
#                     LEFT JOIN hotel_service sl ON sl.booking_id = b.id
#                     GROUP BY b.id
#                 )
#                 SELECT
#                     row_number() OVER () as id,
#                     b.check_in_date as date,
#                     b.room_id as room_id,
#                     b.id as booking_id,
#                     b.partner_id as partner_id,
#                     b.total_amount - COALESCE(bs.service_total, 0) as room_revenue,
#                     COALESCE(bs.service_total, 0) as service_revenue,
#                     b.total_amount as total_revenue
#                 FROM hotel_management_booking b
#                 LEFT JOIN booking_services bs ON bs.booking_id = b.id
#                 WHERE b.state != 'cancelled'
#             )
#         """ % self._table)
# from odoo import models, fields, api
#
#
# class RoomRevenueReport(models.Model):
#     _name = 'hotel.room.revenue.report'
#     _description = 'Room Revenue Report'
#
#     room_id = fields.Many2one('hotel.management.room', string="Room", required=True)
#     total_revenue = fields.Float(string="Total Revenue", compute='_compute_total_revenue', store=True)
#     total_days_used = fields.Integer(string="Total Days Used", compute='_compute_total_revenue', store=True)
#     last_rented_date = fields.Date(string="Last Rented Date", related='room_id.last_rented_date', store=True)
#
#     @api.depends('room_id')
#     def _compute_total_revenue(self):
#         for record in self:
#             # Lấy danh sách bookings liên kết với phòng
#             bookings = self.env['hotel.management.booking'].search([('room_id', '=', record.room_id.id)])
#
#             # Tính tổng doanh thu và tổng số ngày sử dụng
#             record.total_revenue = sum(booking.total_price for booking in bookings)
#             record.total_days_used = sum((booking.check_out_date - booking.check_in_date).days for booking in bookings)
from odoo import models, fields, api, tools
from datetime import datetime, timedelta

class HotelRoomOccupancyReport(models.Model):
    _name = 'hotel.room.occupancy.report'
    _description = 'Room Occupancy Analysis'
    _auto = False

    date = fields.Date(string='Date', readonly=True)
    hotel_id = fields.Many2one('hotel.management.hotel', string='Hotel', readonly=True)
    room_id = fields.Many2one('hotel.management.room', string='Room', readonly=True)
    room_type = fields.Selection(related='room_id.bed_type', string='Room Type', readonly=True)
    state = fields.Selection([
        ('available', 'Available'), ('booked', 'Booked'), ('maintenance', 'Under Maintenance')
    ], string='Status', readonly=True)
    booking_id = fields.Many2one('hotel.management.booking', string='Booking', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    revenue = fields.Float(string='Revenue', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                WITH RECURSIVE dates AS (
                    SELECT DATE(MIN(check_in_date)) AS date
                    FROM hotel_management_booking
                    UNION ALL
                    SELECT date + 1
                    FROM dates
                    WHERE date < CURRENT_DATE + 30
                )
                SELECT
                    row_number() OVER () as id,
                    d.date as date,
                    r.hotel_id as hotel_id,
                    r.id as room_id,
                    CASE
                        WHEN b.id IS NOT NULL AND b.state = 'confirmed' THEN 'booked'
                        WHEN r.state = 'maintenance' THEN 'maintenance'
                        ELSE 'available'
                    END as state,
                    b.id as booking_id,
                    b.customer_id as customer_id,
                    CASE
                        WHEN b.id IS NOT NULL THEN
                            CASE
                                WHEN EXTRACT(DOW FROM d.date) IN (0, 6) THEN r.weekend_price
                                ELSE r.weekday_price
                            END
                        ELSE 0
                    END as revenue
                FROM dates d
                CROSS JOIN hotel_management_room r
                LEFT JOIN hotel_management_booking b ON b.room_id = r.id
                    AND d.date >= b.check_in_date
                    AND d.date < b.check_out_date
                    AND b.state = 'confirmed'
            )
        """ % self._table)

class HotelRevenueReport(models.Model):
    _name = 'hotel.revenue.report'
    _description = 'Revenue Analysis'
    _auto = False

    date = fields.Date(string='Date', readonly=True)
    hotel_id = fields.Many2one('hotel.management.hotel', string='Hotel', readonly=True)
    room_id = fields.Many2one('hotel.management.room', string='Room', readonly=True)
    room_type = fields.Selection(related='room_id.bed_type', string='Room Type', readonly=True)
    booking_id = fields.Many2one('hotel.management.booking', string='Booking', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    room_revenue = fields.Float(string='Room Revenue', readonly=True)
    service_revenue = fields.Float(string='Service Revenue', readonly=True)
    total_revenue = fields.Float(string='Total Revenue', readonly=True)
    week_number = fields.Integer(string='Week Number', readonly=True)
    month = fields.Integer(string='Month', readonly=True)
    year = fields.Integer(string='Year', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                WITH booking_services AS (
                    SELECT
                        b.id as booking_id,
                        sum(s.total_amount) as service_total
                    FROM hotel_management_booking b
                    LEFT JOIN hotel_service s ON s.booking_id = b.id
                    GROUP BY b.id
                )
                SELECT
                    row_number() OVER () as id,
                    b.check_in_date as date,
                    r.hotel_id as hotel_id,
                    b.room_id as room_id,
                    b.id as booking_id,
                    b.customer_id as customer_id,
                    CASE
                        WHEN EXTRACT(DOW FROM b.check_in_date) IN (0, 6) THEN r.weekend_price
                        ELSE r.weekday_price
                    END * (b.check_out_date - b.check_in_date) as room_revenue,
                    COALESCE(bs.service_total, 0) as service_revenue,
                    (CASE
                        WHEN EXTRACT(DOW FROM b.check_in_date) IN (0, 6) THEN r.weekend_price
                        ELSE r.weekday_price
                    END * (b.check_out_date - b.check_in_date)) + COALESCE(bs.service_total, 0) as total_revenue,
                    EXTRACT(WEEK FROM b.check_in_date) as week_number,
                    EXTRACT(MONTH FROM b.check_in_date) as month,
                    EXTRACT(YEAR FROM b.check_in_date) as year
                FROM hotel_management_booking b
                JOIN hotel_management_room r ON r.id = b.room_id
                LEFT JOIN booking_services bs ON bs.booking_id = b.id
                WHERE b.state = 'confirmed'
            )
        """ % self._table)