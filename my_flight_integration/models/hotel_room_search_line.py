from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HotelRoomSearchLine(models.Model):
    _name = "hotel.room.search.line"
    _description = "Hotel Search Line"
    _inherit = ["hotel.api.service"]

    name = fields.Html(string="Room")
    hotel_name = fields.Char("Hotel Name")
    hotel_id = fields.Many2one("hotel.booking.line", "Hotel Name")
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id.id, context={'active_test': False}
    )
    price = fields.Monetary(currency_field='currency_id')
    conf_id = fields.Many2one('booking.conf.line')

    hotel_booking_id = fields.Many2one('hotel.room.search')
    parent_id = fields.Many2one('hotel.room.search')
    booking_code = fields.Char()
    meal_type = fields.Char()

    # Details fields
    refundable = fields.Boolean("Refundable")
    included = fields.Char("Included")
    room_transfer = fields.Char("Room Transfer")
    address = fields.Char("Address")
    rating = fields.Char("Rating")
    description = fields.Text("Description")
    location = fields.Char("Location")

    # HTML fields
    image = fields.Html("Room Image")
    map_view = fields.Html("Map", compute="_compute_map_iframe",store=True,
    sanitize=False)
    raw_json_data = fields.Text()


    # map_iframe = fields.Html("Map", )

    @api.depends("address")
    def _compute_map_iframe(self):
        for rec in self:
            addr = rec.address.replace(" ", "+") if rec.address else ""
            rec.map_view = f"""
                <iframe 
                    src="https://www.google.com/maps?q={addr}&output=embed"
                    width="100%" height="300" style="border:0;">
                </iframe>
            """



    def action_select_room(self):
        self.ensure_one()
        return {
            "name": "Hotel Room Details",
            "type": "ir.actions.act_window",
            "res_model": "hotel.room.wizard",
            "view_mode": "form",
            "target": "new"
        }



    def action_view_more_rooms(self):
        self.ensure_one()
        variant_vals = []

        provider = "GenX"
        parent = self.hotel_booking_id

        try:
            # CALL HOTEL ROOM API BASED ON SELECTED BOOKING CODE
            data = self.call_hotel_api(
                provider,
                "hotel_room",
                BookingCode=self.booking_code,
            )

        except Exception as e:
            raise ValidationError(f"Error fetching hotel details: {e}")


        # Remove previous lines
        if parent.variant_line_ids:
            parent.variant_line_ids.unlink()

        hotel_result = data.get("HotelResult", [])

        if isinstance(hotel_result, dict):
            hotel_result = [hotel_result]

        if not hotel_result:
            raise ValidationError("No Room Result was Found!")


        for hotel in hotel_result:
            rooms = hotel.get("Rooms", {})
            if not rooms:
                continue

            room_transfer = {
                'false' : "Room Transfer Not Available",
                'true' : "Room Transfer Available"
            }
            hotel_id = self.env.context.get("active_hotel_id")

            for room in rooms:
                variant_vals.append({
                    "name": room.get("Name"),
                    "hotel_id": hotel_id,
                    "meal_type": room.get("MealType"),
                    "price": float(room.get("TotalFare") or 0),
                    "included": room.get("Inclusion"),
                    "refundable": room.get("IsRefundable") == "true",
                    'room_transfer': room_transfer.get(room.get("WithTransfers")),
                    "booking_code" : room.get("BookingCode"),
                    "parent_id" : self.hotel_booking_id.id
                })

            # Remove old variants and recreate
            self.create(variant_vals)

        return {
            "name": "More Room Options",
            "type": "ir.actions.act_window",
            "res_model": "hotel.room.search",
            "res_id": self.hotel_booking_id.id,
            "view_mode": "form",
            "view_id": self.env.ref("my_flight_integration.view_hotel_room_more_options").id,
            "domain": [("parent_id", "=", self.hotel_booking_id.id)],
            "target": "current",
        }

