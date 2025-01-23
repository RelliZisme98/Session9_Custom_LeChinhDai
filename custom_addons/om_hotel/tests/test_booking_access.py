from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, timedelta
from odoo import exceptions

class TestBooking(TransactionCase):

    def setUp(self):
        super(TestBooking, self).setUp()

        # Tạo user cho nhóm Manager
        self.manager_user = self.env['res.users'].create({
            'name': 'Manager',
            'login': 'manager',
            'groups_id': [(6, 0, [self.env.ref('hotel.group_hotel_manager').id])]
        })

        # Tạo user cho nhóm Staff
        self.staff_user = self.env['res.users'].create({
            'name': 'Staff',
            'login': 'staff',
            'groups_id': [(6, 0, [self.env.ref('hotel.group_hotel_staff').id])]
        })

    def test_confirm_booking_as_manager(self):
        # Test trường hợp Manager có quyền tạo booking
        with self.env.cr.savepoint():
            self.env = self.env(user=self.manager_user)
            room = self.env['hotel.management.room'].create({'name': 'Room 101'})
            booking = self.env['hotel.management.booking'].create({
                'name': 'Test Booking',
                'check_in_date': '2025-01-01',
                'check_out_date': '2025-01-05',
                'bed_type': 'double',
                'room_id': room.id
            })
            booking.confirm_booking()
            self.assertEqual(booking.state, 'confirmed')

    def test_confirm_booking_as_staff(self):
        # Test trường hợp Staff không được phép tạo booking
        with self.env.cr.savepoint():
            self.env = self.env(user=self.staff_user)
            room = self.env['hotel.management.room'].create({'name': 'Room 102'})
            with self.assertRaises(exceptions.AccessError):
                self.env['hotel.management.booking'].create({
                    'name': 'Unauthorized Booking',
                    'check_in_date': '2025-01-01',
                    'check_out_date': '2025-01-05',
                    'bed_type': 'double',
                    'room_id': room.id
                })

    def test_cancel_booking_as_manager(self):
        # Test Manager có quyền hủy booking
        with self.env.cr.savepoint():
            self.env = self.env(user=self.manager_user)
            room = self.env['hotel.management.room'].create({'name': 'Room 103'})
            booking = self.env['hotel.management.booking'].create({
                'name': 'Test Booking Cancel',
                'check_in_date': '2025-01-01',
                'check_out_date': '2025-01-05',
                'bed_type': 'suite',
                'room_id': room.id
            })
            booking.state = 'confirmed'
            booking.write({'state': 'cancelled'})
            self.assertEqual(booking.state, 'cancelled')

    def test_cancel_booking_as_staff(self):
        # Test Staff không có quyền hủy booking
        with self.env.cr.savepoint():
            self.env = self.env(user=self.staff_user)
            room = self.env['hotel.management.room'].create({'name': 'Room 104'})
            booking = self.env['hotel.management.booking'].create({
                'name': 'Unauthorized Cancel',
                'check_in_date': '2025-01-01',
                'check_out_date': '2025-01-05',
                'bed_type': 'suite',
                'room_id': room.id
            })
            booking.state = 'confirmed'
            with self.assertRaises(exceptions.AccessError):
                booking.write({'state': 'cancelled'})

    def test_room_availability(self):
        # Test không cho phép đặt phòng đã được đặt trước
        with self.env.cr.savepoint():
            self.env = self.env(user=self.manager_user)
            room = self.env['hotel.management.room'].create({'name': 'Room 105'})
            self.env['hotel.management.booking'].create({
                'name': 'First Booking',
                'check_in_date': '2025-01-01',
                'check_out_date': '2025-01-05',
                'bed_type': 'double',
                'room_id': room.id,
                'state': 'confirmed'
            })
            with self.assertRaises(exceptions.ValidationError):
                self.env['hotel.management.booking'].create({
                    'name': 'Overlapping Booking',
                    'check_in_date': '2025-01-04',
                    'check_out_date': '2025-01-06',
                    'bed_type': 'double',
                    'room_id': room.id
                })

    def test_room_under_maintenance(self):
        # Test không cho phép đặt phòng đang bảo trì
        with self.env.cr.savepoint():
            self.env = self.env(user=self.manager_user)
            room = self.env['hotel.management.room'].create({
                'name': 'Room 106',
                'state': 'maintenance'
            })
            with self.assertRaises(exceptions.ValidationError):
                self.env['hotel.management.booking'].create({
                    'name': 'Booking Maintenance Room',
                    'check_in_date': '2025-01-01',
                    'check_out_date': '2025-01-05',
                    'bed_type': 'suite',
                    'room_id': room.id
                })

                # tests/test_hotel_room.py


                class TestHotelRoom(TransactionCase):
                    def setUp(self):
                        super().setUp()
                        self.room = self.env['hotel.management.room'].create({
                            'name': 'Test Room 101',
                            'room_type': 'double',
                            'weekday_price': 100.0,
                            'weekend_price': 150.0,
                            'capacity': 2,
                            'floor': 1
                        })

                        self.partner = self.env['res.partner'].create({
                            'name': 'Test Customer',
                            'email': 'test@example.com'
                        })

                    def test_room_creation(self):
                        """Test room creation and default values"""
                        self.assertEqual(self.room.state, 'available')
                        self.assertEqual(self.room.room_type, 'double')
                        self.assertEqual(self.room.weekday_price, 100.0)

                    def test_room_state_computation(self):
                        """Test room state changes based on bookings"""
                        booking = self.env['hotel.management.booking'].create({
                            'partner_id': self.partner.id,
                            'room_id': self.room.id,
                            'check_in_date': date.today(),
                            'check_out_date': date.today() + timedelta(days=2)
                        })
                        booking.action_confirm()
                        self.assertEqual(self.room.state, 'occupied')

                # tests/test_hotel_booking.py
                class TestHotelBooking(TransactionCase):
                    def setUp(self):
                        super().setUp()
                        self.room = self.env['hotel.management.room'].create({
                            'name': 'Test Room 102',
                            'room_type': 'single',
                            'weekday_price': 80.0,
                            'weekend_price': 120.0
                        })

                        self.partner = self.env['res.partner'].create({
                            'name': 'Test Customer',
                            'email': 'test@example.com'
                        })

                    def test_booking_creation(self):
                        """Test booking creation and validation"""
                        booking = self.env['hotel.management.booking'].create({
                            'partner_id': self.partner.id,
                            'room_id': self.room.id,
                            'check_in_date': date.today(),
                            'check_out_date': date.today() + timedelta(days=3)
                        })
                        self.assertEqual(booking.duration, 3)
                        self.assertEqual(booking.state, 'draft')

                    def test_booking_confirmation(self):
                        """Test booking confirmation process"""
                        booking = self.env['hotel.management.booking'].create({
                            'partner_id': self.partner.id,
                            'room_id': self.room.id,
                            'check_in_date': date.today(),
                            'check_out_date': date.today() + timedelta(days=1)
                        })
                        booking.action_confirm()
                        self.assertEqual(booking.state, 'confirmed')
                        self.assertTrue(booking.sale_order_id, "Sale order should be created")

                    def test_overlapping_bookings(self):
                        """Test prevention of overlapping bookings"""
                        booking1 = self.env['hotel.management.booking'].create({
                            'partner_id': self.partner.id,
                            'room_id': self.room.id,
                            'check_in_date': date.today(),
                            'check_out_date': date.today() + timedelta(days=2)
                        })
                        booking1.action_confirm()

                        with self.assertRaises(ValidationError):
                            booking2 = self.env['hotel.management.booking'].create({
                                'partner_id': self.partner.id,
                                'room_id': self.room.id,
                                'check_in_date': date.today() + timedelta(days=1),
                                'check_out_date': date.today() + timedelta(days=3)
                            })
                            booking2.action_confirm()

                # tests/test_hotel_services.py
                class TestHotelServices(TransactionCase):
                    def setUp(self):
                        super().setUp()
                        self.room = self.env['hotel.management.room'].create({
                            'name': 'Test Room 103',
                            'room_type': 'suite',
                            'weekday_price': 200.0,
                            'weekend_price': 300.0
                        })

                        self.product = self.env['product.product'].create({
                            'name': 'Room Service',
                            'type': 'service',
                            'list_price': 50.0
                        })

                        self.booking = self.env['hotel.management.booking'].create({
                            'partner_id': self.partner.id,
                            'room_id': self.room.id,
                            'check_in_date': date.today(),
                            'check_out_date': date.today() + timedelta(days=1)
                        })

                    def test_service_addition(self):
                        """Test adding services to booking"""
                        service_line = self.env['hotel.service'].create({
                            'booking_id': self.booking.id,
                            'product_id': self.product.id,
                            'quantity': 2,
                            'unit_price': 50.0
                        })
                        self.assertEqual(service_line.price_total, 100.0)
                        self.booking.action_confirm()
                        self.assertIn(
                            self.product.name,
                            self.booking.sale_order_id.order_line.mapped('name')
                        )