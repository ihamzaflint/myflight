from odoo import models, fields
from odoo.exceptions import ValidationError


class HotelBookingDetail(models.Model):
    _name = "hotel.booking.detail"
    _description = "Hotel Booking Detailed Info"
    _rec_name = "booking_reference_id"


    hotel_search_id = fields.Many2one("hotel.room.search")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
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

    cancellation_date = fields.Date("From Date")
    cancellation_type = fields.Char("Charge Type")
    cancellation_charge = fields.Char("Cancellation Charges")

    hotel_id = fields.Many2one("hotel.booking.line", "Hotel")
    hotel_rating = fields.Char()
    city_id = fields.Many2one("res.country.city", "City")

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id.id, context={'active_test': False}
    )

    raw_response = fields.Text()
    desc = fields.Text("Description")

    guest_line_ids = fields.One2many(
        "hotel.guest.detail.line",
        "detail_id",
        string="Guest Details"
    )

    room_line_ids = fields.One2many(
        "hotel.room.search.line",
        "hotel_detail_id",
        string="Room Lines"
    )


    def action_cancel_booking(self):
        self.ensure_one()

        if not self.confirmation_number:
            raise ValidationError("Confirmation number missing, cannot cancel booking.")

        return {
            "type": "ir.actions.act_window",
            "res_model": "hotel.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_booking_detail_id": self.id,
                "default_confirmation_number": self.confirmation_number,
                "default_text": "Are you sure you want to cancel booking?",
            }
        }