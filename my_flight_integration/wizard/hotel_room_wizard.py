from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class HotelRoomWizard(models.TransientModel):
    _name = "hotel.room.wizard"
    _description = "Hotel Room Wizard"
    _inherit = ["hotel.api.service"]


    name = fields.Html()
    hotel_room_search_line_id = fields.Many2one("hotel.room.search.line", string="Hotel Room", readonly=True)
    total_price = fields.Monetary(string="Total Price", currency_field='currency_id', readonly=True)
    currency = fields.Char(string="Currency", readonly=True)
    total_tax = fields.Char(string="Total Tax")
    meal_type = fields.Char()
    amenities = fields.Text(string="Amenities")
    booking_code = fields.Char()

    # Cancel policy fields for hotel
    from_date = fields.Date(string="From Date")
    charge_type = fields.Char(string="Charge Type")
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id.id, context={'active_test': False}
    )
    cancellation_charge = fields.Monetary("Cancellation Charges", currency_field='currency_id')
    raw_json_data = fields.Text()
    desc = fields.Char("Description")
    not_bookable = fields.Boolean()


    def action_add_guest_details(self):
        """
        Opens the traveller form of hotel.room.search
        """
        self.ensure_one()

        hotel_search_id = self.hotel_room_search_line_id.parent_id

        return {
            "name": "Guest Details",
            "type": "ir.actions.act_window",
            "res_model": "hotel.room.search",
            "view_mode": "form",
            "res_id": hotel_search_id.id,
            "target": "new",
            "view_id": self.env.ref("my_flight_integration.view_hotel_room_search_traveller_guest_details_form").id,
            "context": {
                "return_to_prebook": True,
                "active_wizard_id": self.id,
            }
        }


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")

        if not active_id:
            return res

        provider = "GenX"

        try:
            line = self.env["hotel.room.search.line"].browse(active_id)
            res["hotel_room_search_line_id"] = line.id

            # ==== PREBOOK API ====
            data = self.call_hotel_api(
                provider,
                "prebook",
                BookingCode=line.booking_code
            )

        except Exception as e:
            raise ValidationError(f"Error fetching hotel details: {e}")

        status = data.get("Status", {})
        code = status.get("Code")
        desc = status.get("Description")

        # Rate not bookable
        if code == "403":
            res["not_bookable"] = True

        hotel_result = data.get("HotelResult")
        if not hotel_result:
            raise ValidationError("No Result Found!")

        room = hotel_result.get("Rooms")
        if not room:
            raise ValidationError("No room(s) found!")

        currency_rec = self.env["res.currency"].search(
            [("name", "=", hotel_result.get("Currency"))], limit=1
        )

        # Cancel policies
        # have to do changes for multiple cancellation policy
        cancel_policy_raw = room.get("CancelPolicies") or []

        # Normalize to list
        if isinstance(cancel_policy_raw, dict):
            cancel_policies = [cancel_policy_raw]
        elif isinstance(cancel_policy_raw, list):
            cancel_policies = cancel_policy_raw
        else:
            cancel_policies = []


        policy = cancel_policies[0] if cancel_policies else {}


        from_date = datetime.strptime(
            policy.get("FromDate"), "%d-%b-%Y"
        ).strftime("%Y-%m-%d")

        amenities = ", ".join(room.get("Amenities", []))

        # ==== Update Wizard Fields ====
        res.update({
            "name": room.get("Name"),
            "total_price": float(room.get("TotalFare")),
            "total_tax": float(room.get("TotalTax")),
            "amenities": amenities,
            "meal_type": room.get("MealType"),
            "currency_id": currency_rec.id if currency_rec else False,
            "from_date": from_date,
            "charge_type": policy.get("ChargeType"),
            "cancellation_charge": policy.get("CancellationCharge"),
            "desc": desc or "",
        })

        return res


    def action_book_room(self):
        self.ensure_one()
        provider = "GenX"

        # ================= SEQUENCES =================
        client_ref_id = self.env["ir.sequence"].next_by_code("hotel.client.ref2")
        booking_ref_id = self.env["ir.sequence"].next_by_code("hotel.booking.ref2")

        if not client_ref_id or not booking_ref_id:
            raise ValidationError("Reference Sequences not configured!")

        # ================= CUSTOMER DETAILS =================
        customer_details = []

        traveller_lines = self.hotel_room_search_line_id.parent_id.traveller_line_ids

        for room in traveller_lines:
            room_guests = []
            for guest in room.hotel_room_guest_detail_line_ids:
                room_guests.append({
                    "Title": guest.title or "",
                    "FirstName": guest.first_name or "",
                    "LastName": guest.last_name or "",
                    "Type": "Adult" if guest.traveller_type == "adult" else "Child"
                })

            customer_details.append({
                "CustomerNames": room_guests
            })

        # ================= LEAD GUEST =================
        all_guests = traveller_lines.mapped("hotel_room_guest_detail_line_ids")

        lead_guest = all_guests.filtered(lambda g: g.traveller_type == "adult")[:1]
        if not lead_guest:
            lead_guest = all_guests[:1]

        first_room = traveller_lines[:1]
        email = lead_guest.partner_id.email or first_room.email
        phone = lead_guest.partner_id.phone or first_room.phone


        # ================= FINAL PAYLOAD =================
        payload = {
            "BookingCode": self.hotel_room_search_line_id.booking_code,
            "CustomerDetails": customer_details,
            "BookingType": "Voucher",
            "ClientReferenceId": client_ref_id,
            "BookingReferenceId": booking_ref_id,
            "PaymentMode": "Limit",
            "GuestNationality": "AE",
            "TotalFare": self.total_price,
            "EmailId": email,
            "PhoneNumber": phone,
        }

        _logger.info("\n\nHOTEL BOOK PAYLOAD =====\n%s\n", payload)

        response = self.call_hotel_api(provider, "book", **payload)

        if not response:
            raise ValidationError("Booking API returned empty response!")

        # -------------------- CALL BOOKING DETAILS API --------------------
        details_payload = {
            "PaymentMode": "Limit",
            "BookingReferenceId": booking_ref_id
        }

        details = self.call_hotel_api(provider, "booking_detail", **details_payload)

        if not details:
            raise ValidationError("Booking Details API returned empty response!")

        booking_detail = details.get("BookingDetail")
        if not booking_detail:
            raise ValidationError("BookingDetail not found in API response!")


        api_booking_status_map = {
            "Pending" : "pending",
            "Failed" : "failed",
            "Confirmed" : "confirmed",
        }



        hotel_search_id = self.hotel_room_search_line_id.parent_id

        check_in = datetime.strptime(booking_detail.get("CheckIn"), "%d %b %Y").date()
        check_out = datetime.strptime(booking_detail.get("CheckOut"), "%d %b %Y").date()
        booking_date = datetime.strptime(booking_detail.get("BookingDate"), "%d %b %Y").date()

        # -------------------- SAVE IN MODEL --------------------
        detail_record = self.env["hotel.booking.detail"].create({
            "hotel_search_id" : hotel_search_id.id,
            "booking_reference_id": booking_ref_id,
            "payment_mode": "Limit",
            "confirmation_number": booking_detail.get("ConfirmationNumber"),
            "invoice_number": booking_detail.get("InvoiceNumber"),
            "state": api_booking_status_map.get(booking_detail.get("BookingStatus")),
            "voucher_status": booking_detail.get("VoucherStatus"),

            "check_in": check_in,
            "check_out": check_out,
            "booking_date": booking_date,
            "no_of_rooms": int(booking_detail.get("NoOfRooms", 0)),

            "hotel_name": booking_detail.get("HotelDetails", {}).get("HotelName"),
            "hotel_rating": booking_detail.get("HotelDetails", {}).get("Rating"),
            "hotel_city": booking_detail.get("HotelDetails", {}).get("City"),

            # "room_name": booking_detail.get("Rooms", {}).get("Name"),
            # "room_meal_type": booking_detail.get("Rooms", {}).get("MealType"),
            # "room_fare": float(booking_detail.get("Rooms", {}).get("TotalFare", 0)),
            # # "total_tax": float(booking_detail.get("Rooms", {}).get("TotalTax") or 0),
            # "room_is_refundable": booking_detail.get("Rooms", {}).get("IsRefundable"),

            "raw_response": str(booking_detail.get("Rooms", {}).get("CustomerDetails")),
        })

        # ================= UPDATE HOTEL SEARCH STATUS =================
        hotel_search_id.state = "confirmed"

        # -------------------- OPEN SAVED RECORD --------------------
        return {
            "type": "ir.actions.act_window",
            "res_model": "hotel.booking.detail",
            "view_mode": "form",
            "res_id": detail_record.id,
            "target": "current",
        }
