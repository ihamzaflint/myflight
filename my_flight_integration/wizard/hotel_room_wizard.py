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
    api_status = fields.Char("API Status")
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
        else:
            cancel_policies = cancel_policy_raw

        # Final list to put in wizard
        policy_values = []

        room_search_line_id = self.env["hotel.room.search.line"].browse(self.env.context.get("default_hotel_room_search_line_id"))
        traveller_lines = room_search_line_id.parent_id.traveller_line_ids

        multiple = len(traveller_lines) > 1

        for idx, pol in enumerate(cancel_policies, start=1):
            from_date = False
            if pol.get("FromDate"):
                try:
                    # Convert 03-Dec-2025 → 2025-12-03
                    from_date = datetime.strptime(pol["FromDate"], "%d-%b-%Y").date()
                except Exception:
                    from_date = False

            charge = float(pol.get("CancellationCharge", 0.0))

            # If multiple policies → add prefix like R1, R2
            label_prefix = f"R{idx} - " if multiple else f"{idx} - "

            policy_values.append({
                "label": f"{label_prefix}{pol.get('ChargeType', '')}",
                "from_date": from_date,
                "charge_type": pol.get("ChargeType", ""),
                "cancellation_charge": charge,
            })

        if len(policy_values) == 1:
            p = policy_values[0]
            res.update({
                "from_date": p["from_date"],
                "charge_type": p["charge_type"],
                "cancellation_charge": p["cancellation_charge"],
                "api_status": desc
            })
        else:
            # Convert list of policies into readable multiline text
            policy_text = "\n".join(
                f"{p['label']} | From: {p['from_date']} | Charge: {p['cancellation_charge']} | Type: {p['charge_type']}"
                for p in policy_values
            )

            # Show first policy in main fields
            first = policy_values[0]
            cancellation_charge = sum(p.get("cancellation_charge") for p in policy_values)

            res.update({
                "from_date": first["from_date"],
                "charge_type": first["charge_type"],
                "cancellation_charge": cancellation_charge,
                "desc": "CANCELLATION POLICIES:\n\n" + "\n" + policy_text,
                "api_status": desc,
            })


        # policy = cancel_policies[0] if cancel_policies else {}
        #
        #
        # from_date = datetime.strptime(
        #     policy.get("FromDate"), "%d-%b-%Y"
        # ).strftime("%Y-%m-%d")

        amenities = ", ".join(room.get("Amenities", []))

        # ==== Update Wizard Fields ====
        res.update({
            "name": room.get("Name"),
            "total_price": float(room.get("TotalFare")),
            "total_tax": float(room.get("TotalTax")),
            "amenities": amenities,
            "meal_type": room.get("MealType"),
            "currency_id": currency_rec.id if currency_rec else False
        })

        return res


    def action_book_room(self):
        self.ensure_one()
        provider = "GenX"

        # ================= SEQUENCES =================
        client_ref_id = self.env["ir.sequence"].next_by_code("hotel.client.seq")
        booking_ref_id = self.env["ir.sequence"].next_by_code("hotel.booking.seq")

        # client_ref_id = self.env["ir.sequence"].next_by_code("hotel.client.ref2")
        # booking_ref_id = self.env["ir.sequence"].next_by_code("hotel.booking.ref2")

        if not client_ref_id or not booking_ref_id:
            raise ValidationError("Reference Sequences not configured!")

        # ================= CUSTOMER DETAILS =================
        customer_details = []

        room_search_line_id = self.hotel_room_search_line_id

        traveller_lines = room_search_line_id.parent_id.traveller_line_ids

        for room in traveller_lines:
            if not room.hotel_room_guest_detail_line_ids:
                raise ValidationError(
                    "Guest details are required before booking!\n"
                    f"Room with {room.adults} adult(s) and {room.children} child(ren) has no guest details."
                )

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

        email = first_room.lead_email or lead_guest.partner_id.email
        phone =  first_room.lead_phone or lead_guest.partner_id.phone


        # ================= FINAL PAYLOAD =================
        payload = {
            "BookingCode": self.hotel_room_search_line_id.booking_code,
            "CustomerDetails": customer_details,
            "BookingType": "Voucher",
            "ClientReferenceId": client_ref_id,
            "BookingReferenceId": booking_ref_id,
            "PaymentMode": "Limit",
            "GuestNationality": room_search_line_id.parent_id.guest_nationality_id.code or "AE",
            "TotalFare": self.total_price,
            "EmailId": email,
            "PhoneNumber": phone,
        }

        _logger.info("\n\nHOTEL BOOK PAYLOAD =====\n%s\n", payload)

        response = self.call_hotel_api(provider, "book", **payload)

        if not response:
            raise ValidationError("Booking API returned empty response!")

        # -------------------- CALL BOOKING DETAILS API --------------------
        if response.get("Status").get("Code") == '200':

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
                "Cancelled" : "cancelled",
            }

            hotel_search_id = self.hotel_room_search_line_id.parent_id

            check_in = datetime.strptime(booking_detail.get("CheckIn"), "%d %b %Y").date()
            check_out = datetime.strptime(booking_detail.get("CheckOut"), "%d %b %Y").date()
            booking_date = datetime.strptime(booking_detail.get("BookingDate"), "%d %b %Y").date()

            room = booking_detail.get("Rooms")
            if not room:
                raise ValidationError("Room Detail not found in API response!")


            cancel_policy_raw = room.get("CancelPolices") or []

            # Normalize to list
            if isinstance(cancel_policy_raw, dict):
                cancel_policies = [cancel_policy_raw]
            else:
                cancel_policies = cancel_policy_raw

            policy_values = []

            multiple = len(cancel_policies) > 1   # multiple policies → show R1 / R2

            for idx, pol in enumerate(cancel_policies, start=1):

                # Clean date safely
                from_date = False
                if pol.get("FromDate"):
                    try:
                        for fmt in ("%d-%b-%Y", "%d %b %Y", "%d %B %Y"):
                            try:
                                from_date = datetime.strptime(pol["FromDate"], fmt).date()
                            except:
                                from_date = datetime.strptime(pol["FromDate"], "%d %b %Y").date()
                    except:
                        from_date = False

                cancellation_charge = float(pol.get("CancellationCharge", 0.0))

                # Prefix
                label_prefix = f"R{idx} - " if multiple else f"{idx} - "

                policy_values.append({
                    "label": f"{label_prefix}{pol.get('ChargeType', '')}",
                    "from_date": from_date,
                    "charge_type": pol.get("ChargeType", ""),
                    "cancellation_charge": cancellation_charge,
                })

            # ---------- Build cancellation text ----------

            if len(policy_values) == 1:
                # Single policy
                p = policy_values[0]

                cancellation_date = p["from_date"]
                cancellation_type = p["charge_type"]
                cancellation_charge = p["cancellation_charge"]

                cancellation_desc = f"CANCELLATION POLICY:\n" \
                                    f"From: {p['from_date']}\n" \
                                    f"Charge: {p['cancellation_charge']}\n" \
                                    f"Type: {p['charge_type']}"

            else:
                # Multiple policies
                cancellation_date = policy_values[0]["from_date"]
                cancellation_type = policy_values[0]["charge_type"]
                cancellation_charge = sum(p["cancellation_charge"] for p in policy_values)

                lines = []
                for p in policy_values:
                    lines.append(
                        f"{p['label']} | From: {p['from_date']} | "
                        f"Charge: {p['cancellation_charge']} | Type: {p['charge_type']}"
                    )

                cancellation_desc = "CANCELLATION POLICIES:\n\n" + "\n".join(lines)

            # -------------------- SAVE IN MODEL --------------------

            detail_record = self.env["hotel.booking.detail"].create({
                "hotel_search_id": hotel_search_id.id,
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

                "cancellation_date": cancellation_date,
                "cancellation_type": cancellation_type,
                "cancellation_charge": cancellation_charge,

                "hotel_id": self.hotel_room_search_line_id.hotel_id.id,
                "city_id": self.hotel_room_search_line_id.hotel_id.city_id.id,
                "hotel_rating": booking_detail.get("HotelDetails", {}).get("Rating"),

                "raw_response": str(booking_detail.get("Rooms", {}).get("CustomerDetails")),
            })

            # Save the description separately if you want inside detail model:
            detail_record.desc = cancellation_desc

            # Add uest Details in Booking Details
            guest_vals = []
            for guest in all_guests:
                guest_vals.append((0, 0, {
                    "title": guest.title,
                    "partner_id": guest.partner_id.id,
                    "dob": guest.dob,
                    "traveller_type": guest.traveller_type,
                    "detail_id": detail_record.id,
                }))

            detail_record.write({
                "guest_line_ids": guest_vals
            })


            # Add room details in Booking Details
            room_search_line_id.copy({
                "hotel_detail_id" : detail_record.id,
                "hotel_booking_id" : False
            })

            # ================= UPDATE HOTEL SEARCH STATUS =================

            if details.get("Status").get("Code") == '200':
                hotel_search_id.state = "confirmed"
            hotel_search_id.write({"hotel_detail_id": detail_record.id})

            # -------------------- OPEN SAVED RECORD --------------------
            return {
                "type": "ir.actions.act_window",
                "res_model": "hotel.booking.detail",
                "view_mode": "form",
                "res_id": detail_record.id,
                "target": "current",
            }
