odoo.define('hotel_management.pos_hotel', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');

    class HotelBookingButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }

        async onClick() {
            const bookings = await this.rpc({
                model: 'hotel.management_booking',
                method: 'search_read',
                args: [[['state', '=', 'checked_in']]],
            });

            const { confirmed, payload } = await this.showPopup('SelectionPopup', {
                title: 'Select Booking',
                list: bookings.map(booking => ({
                    id: booking.id,
                    label: `${booking.name} - Room ${booking.room_id[1]}`,
                    item: booking,
                })),
            });

            if (confirmed) {
                this.env.pos.set_hotel_management_booking(payload);
            }
        }
    }
    Registries.Component.add(HotelBookingButton);