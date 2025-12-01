from odoo import models, fields

class HotelBookingDetail(models.Model):
    _name = "hotel.booking.detail"
    _description = "Hotel Booking Detailed Info"
    _rec_name = "hotel_search_id"

    hotel_search_id = fields.Many2one("hotel.room.search")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('confirmed', 'Confirmed'),
    ], string="Status", default='draft')

    booking_reference_id = fields.Char()
    payment_mode = fields.Char()
    # booking_status = fields.Char()
    voucher_status = fields.Char()
    confirmation_number = fields.Char()
    invoice_number = fields.Char()


    check_in = fields.Date()
    check_out = fields.Date()
    booking_date = fields.Date()
    no_of_rooms = fields.Integer()

    # hotel_id = fields.Many2one("hotel.booking.line", "Hotel")
    hotel_name = fields.Char()
    hotel_rating = fields.Char()
    hotel_city = fields.Char()
    # city_id = fields.Many2one("res.country.city", "City")

    # room_id = fields.Many2one("hotel.room.search.line", "Room")
    room_name = fields.Char()
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id.id, context={'active_test': False}
    )
    # room_fare = fields.Float()
    # room_meal_type = fields.Char()
    # room_is_refundable = fields.Char()
    #
    # cancellation_from_date = fields.Char()
    # cancellation_charge_type = fields.Char()
    # cancellation_amount = fields.Char()
    #
    # lead_guest_title = fields.Char()
    # lead_guest_first_name = fields.Char()
    # lead_guest_last_name = fields.Char()
    # lead_guest_type = fields.Char()

    raw_response = fields.Text()
