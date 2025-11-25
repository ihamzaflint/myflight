from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class HotelRoomWizard(models.TransientModel):
    _name = "hotel.room.wizard"
    _description = "Hotel Room Wizard"
    _inherit = ["hotel.api.service"]


    name = fields.Char()
    hotel_room_search_line_id = fields.Many2one("hotel.room.search.line", string="Hotel Room", readonly=True)
    total_price = fields.Char(string="Total Price", readonly=True)
    currency = fields.Char(string="Currency", readonly=True)
    total_tax = fields.Char(string="Total Tax")
    meal_type = fields.Char()
    amenities = fields.Text(string="Amenities")
    booking_code = fields.Char()

    # Cancel policy fields for hotel
    from_date = fields.Date(string="From Date")
    charge_type = fields.Char(string="Charge Type")
    cancellation_charge = fields.Float(string="Cancellation Charges")
    raw_json_data = fields.Text()
    desc = fields.Char()


    def action_add_guest_details(self):
        """
        Opens the traveller form of hotel.room.search
        """
        self.ensure_one()

        hotel_search = self.hotel_room_search_line_id.hotel_booking_id

        return {
            "name": "Add Travellers",
            "type": "ir.actions.act_window",
            "res_model": "hotel.room.search",
            "view_mode": "form",
            "res_id": hotel_search.id,
            "target": "new",
            "view_id": self.env.ref("my_flight_integration.view_hotel_room_search_traveller_guest_details_form").id,
        }


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')

        if not active_id:
            return res

        provider = "smart booking"

        if provider in ["smart booking", "GenX"]:

            try:
                hotel_room_search_line_id = self.env["hotel.room.search.line"].browse(active_id)
                res["hotel_room_search_line_id"] = hotel_room_search_line_id.id
                # self.hotel_room_search_line_id = hotel_room_search_line_id.id

                data = self.call_hotel_api(
                    provider,
                    "prebook",
                    BookingCode=hotel_room_search_line_id.booking_code
                )
            except Exception as e:
                raise ValidationError(f"Error fetching hotel details: {e}")


            code = data.get("Status").get("Code")
            desc = data.get("Status").get("Description")
            # if code != "200":
            #     raise ValidationError(f"Prebook failed: {desc}")

            hotel_result = data.get("HotelResult")

            if not hotel_result:
                raise ValidationError("No Result Found!")

            room = hotel_result.get("Rooms", {})

            if not room:
                raise ValidationError("No room(s) Found!")


            cancellation_policies = room.get("CancelPolicies", {})
            date_part = cancellation_policies.get("FromDate")
            from_date = datetime.strptime(date_part, "%d-%b-%Y").strftime("%Y-%m-%d")

            res.update({
                "name" : room.get("Name"),
                "total_price" : room.get("TotalFare"),
                "total_tax" : room.get("TotalTax"),
                "amenities" : room.get("Amenities"),
                "meal_type" : room.get('MealType', False),
                "currency" : hotel_result.get("Currency"),
                "from_date" : from_date,
                "charge_type" : cancellation_policies.get("ChargeType"),
                "cancellation_charge" : cancellation_policies.get("CancellationCharge"),
                "desc" : desc
            })


        return res