from odoo import models, fields, api
from datetime import date
import json
import requests
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class HotelRoomSearch(models.Model):
    _name = "hotel.room.search"
    _description = "Hotel Search"
    _inherit = ["hotel.api.service"]
    _rec_name = "display_name"

    display_name = fields.Char(string="Display Name", compute="_compute_display_name", store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('searched', 'Searched'),
        ('result_found', 'Result Found'),
        ('not_found', 'Result Not Found'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string="Status", default='draft')

    check_in = fields.Date(string="Check In")
    check_out = fields.Date(string="Check Out")
    country_id = fields.Many2one('res.country', string="Country")
    city_id = fields.Many2one('res.country.city', string="City", domain="[('country_id', '=', country_id)]")
    hotel_line_ids = fields.Many2many('hotel.booking.line', 'booking_search_hotel_line_rel', 'booking_search_id', 'hotel_id', string="Hotels", domain="[('country_id', '=', country_id), ('city_id', '=', city_id)]")
    guest_nationality_id = fields.Many2one('res.country', string="Guest Nationality", default=lambda self: self.env.company.country_id.id)

    line_ids = fields.One2many('hotel.room.search.line', 'hotel_booking_id')
    variant_line_ids = fields.One2many(
        "hotel.room.search.line",
        "parent_id",
        string="Room Variants"
    )
    hotel_detail_id = fields.Many2one("hotel.booking.detail", "Booking Details")

    # Traveller data
    traveller_line_ids = fields.One2many(
        'hotel.room.traveller.line',
        'hotel_room_search_id',
        string="Travellers"
    )

    total_rooms = fields.Integer(compute="_compute_totals")
    total_adults = fields.Integer(compute="_compute_totals")
    total_children = fields.Integer(compute="_compute_totals")


    @api.onchange("country_id")
    def _onchange_country(self):
        """When country changes → clear city & hotels"""
        self.city_id = False
        self.hotel_line_ids = [(5, 0, 0)]


    @api.depends('traveller_line_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_rooms = len(rec.traveller_line_ids)
            rec.total_adults = sum(rec.traveller_line_ids.mapped('adults'))
            rec.total_children = sum(rec.traveller_line_ids.mapped('children'))


    @api.depends('check_in', 'check_out', 'country_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                rec.display_name = f"Hotel Booking [{rec.check_in} → {rec.check_out}]"
            else:
                rec.display_name = "Hotel Booking"


    def action_search_hotel_rooms(self):
        self.ensure_one()

        if not self.country_id:
            raise ValidationError("Please select a country.")
        if not self.city_id:
            raise ValidationError("Please select a city.")

        provider = "GenX"
        hotel_lines = []

        if provider in ["GenX"]:
            hotel_codes = ",".join(self.hotel_line_ids.mapped("code"))

            pax_rooms = []

            for room in self.traveller_line_ids:
                pax_rooms.append({
                    "Adults": room.adults,
                    "Children": room.children,
                    "ChildrenAges": [int(x) for x in room.children_ages.split(",")] if room.children else []
                })

            try:
                data = self.call_hotel_api(
                    provider,
                    "search",
                    CheckIn=self.check_in.strftime("%Y-%m-%d") if isinstance(self.check_in, date) else self.check_in,
                    CheckOut=self.check_out.strftime("%Y-%m-%d") if isinstance(self.check_out, date) else self.check_out,
                    HotelCodes=hotel_codes,
                    GuestNationality=self.guest_nationality_id.code,
                    PaxRooms=pax_rooms,
                )
            except Exception as e:
                raise ValidationError(f"Error fetching hotel details: {e}")

            # Normalize hotel result to a list
            hotel_result = data.get("HotelResult", [])

            if isinstance(hotel_result, dict):
                hotel_result = [hotel_result]

            # Remove previous lines
            if self.line_ids:
                self.line_ids.unlink()

            # Create hotel lines
            for hotel in hotel_result:

                room_transfer = {
                    'false' : "Room Transfer Not Available",
                    'true' : "Room Transfer Available"
                }

                hotel_code = hotel.get("HotelCode")
                rooms = hotel.get("Rooms", {})
                if not rooms:
                    continue

                # If Rooms is a dict, convert to list for uniformity
                if isinstance(rooms, dict):
                    rooms = [rooms]

                for room in rooms:
                    img = hotel.get("FrontImage")
                    html_images = ""
                    if img:
                        html_images = f'<img src="{img}" style="width:200px;height:150px;border-radius:6px;"/>'


                    currency_id = self.env['res.currency'].search([('name', '=', hotel.get("Currency"))])

                    hotel_id = self.env["hotel.booking.line"].search([('code', '=', hotel_code)])

                    vals = {
                        'hotel_name': hotel.get("HotelName"),
                        'hotel_id': hotel_id.id,
                        'name': room.get("Name"),
                        'price': float(room.get("TotalFare") or 0),
                        'currency_id': currency_id.id,
                        'meal_type': room.get("MealType"),
                        'booking_code': room.get("BookingCode"),
                        'hotel_booking_id': self.id,

                        # details
                        'address': hotel.get("Address"),
                        'rating': hotel.get("StarRating"),
                        'description': hotel.get("HotelDesc"),
                        'location': hotel.get("Location"),
                        'room_transfer': room_transfer.get(room.get("WithTransfers")),
                        'included' : room.get("Inclusion"),
                        'refundable': True if room.get("IsRefundable").lower() == 'true' else False,

                        # html
                        'image': html_images,
                        'raw_json_data': json.dumps(room),
                    }
                    hotel_lines.append(vals)

            if not hotel_lines:
                self.state = 'not_found'
                raise ValidationError("No valid hotel room records found to create.")

            # Create all lines in one batch
            self.env['hotel.room.search.line'].create(hotel_lines)
            self.state = 'result_found'


    def action_open_travellers(self):
        for rec in self:
            if not rec.traveller_line_ids:
                rec.write({
                    "traveller_line_ids": [(0, 0, {
                        "adults": 1,
                        "children": 0,
                        "children_ages": "",
                        "hotel_room_search_id" : rec.id
                    })]
                })
        return {
            "name": "Add Rooms",
            "type": "ir.actions.act_window",
            "res_model": "hotel.room.search",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "view_id": self.env.ref("my_flight_integration.view_hotel_room_search_traveller_add_room_form").id
        }


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Add default traveller line only if not already added
        if "traveller_line_ids" in fields_list:
            traveller_id = {
                "adults": 1,
                "children": 0,
                "children_ages": "",
            }

            res["traveller_line_ids"] = [(0, 0, traveller_id)]

        return res


    def action_return_prebook(self):
        wizard_id = self.env.context.get("active_wizard_id")
        return {
            "type": "ir.actions.act_window",
            "res_model": "hotel.room.wizard",
            "view_mode": "form",
            "res_id": wizard_id,
            "target": "new",
        }



class HotelRoomTravellerLine(models.Model):
    _name = "hotel.room.traveller.line"
    _description = "Traveller Details Per Room"

    hotel_room_search_id = fields.Many2one("hotel.room.search", ondelete="cascade")

    adults = fields.Integer("Adults", default=1)
    children = fields.Integer("Children")
    children_ages = fields.Char("Children Ages", help="Enter ages between 1 and 12. "
             "For multiple ages, use comma-separated values. Example: 5,8,17")


    lead_email = fields.Char("Lead Person Email", compute="compute_lead_email_phone", readonly=False)
    lead_phone = fields.Char("Lead Person Phone", compute="compute_lead_email_phone", readonly=False)

    hotel_room_guest_detail_line_ids = fields.One2many("hotel.guest.detail.line", "room_traveller_line_id", "Guest Details")


    @api.constrains('children_ages', 'children')
    def _check_children_age(self):
        for rec in self:
            # If no children → age field must be empty
            if rec.children == 0:
                if rec.children_ages:
                    raise ValidationError("No children selected, so age field must be empty.")
                continue

            # Children > 0 → Age must be entered
            if rec.children > 0 and not rec.children_ages:
                raise ValidationError("Please enter age(s) of the children.")

            # Parse comma-separated ages
            try:
                age_list = [int(a.strip()) for a in rec.children_ages.split(",") if a.strip()]
            except Exception:
                raise ValidationError("Invalid age format. Use comma-separated numbers like: 5,7,17.")

            # Check number of ages equals number of children
            if len(age_list) != rec.children:
                raise ValidationError(
                    f"You entered {len(age_list)} ages but selected {rec.children} children."
                )

            # Validate age range
            for age in age_list:
                if age < 1 or age > 17:
                    raise ValidationError("Child age must be between 1 and 12.")


    @api.constrains("adults", "children")
    def _check_room_capacity(self):
        for room in self:
            if room.adults > 4:
                raise ValidationError(
                    "Maximum 4 adults allowed per room."
                )

            if (room.adults + room.children) > 5:
                raise ValidationError(
                    "A room can have maximum 5 guests (adults + children)."
                )


    @api.constrains("hotel_room_guest_detail_line_ids", "adults", "children")
    def _check_guest_counts(self):
        for rec in self:

            if not rec.hotel_room_guest_detail_line_ids:
                return

            guest_lines = rec.hotel_room_guest_detail_line_ids

            # Count adults & children from guest detail lines
            adult_count = sum(1 for g in guest_lines if g.traveller_type == "adult")
            child_count = sum(1 for g in guest_lines if g.traveller_type == "child")

            # Validate adult count
            if adult_count != rec.adults:
                raise ValidationError(
                    f"Adult count mismatch! You selected {rec.adults} adults "
                    f"but entered {adult_count} adult guest details."
                )

            # Validate child count
            if child_count != rec.children:
                raise ValidationError(
                    f"Child count mismatch! You selected {rec.children} children "
                    f"but entered {child_count} child guest details."
                )

    @api.depends('hotel_room_guest_detail_line_ids')
    def compute_lead_email_phone(self):
        for rec in self:
            if rec.lead_email or rec.lead_phone:
                continue

            # Default values
            rec.lead_email = ""
            rec.lead_phone = ""


            guests = rec.hotel_room_guest_detail_line_ids

            if not guests:
                continue

            # Prefer an adult guest as lead
            lead_guest = guests.filtered(lambda g: g.traveller_type == "adult")[:1]

            # If no adult, pick the first guest
            if not lead_guest:
                lead_guest = guests[:1]

            lead_guest = lead_guest[0]

            # Extract from partner
            if lead_guest.partner_id:
                rec.lead_email = lead_guest.partner_id.email or ""
                rec.lead_phone = lead_guest.partner_id.phone or ""




class HotelGuestDetailsLine(models.Model):
    _name = "hotel.guest.detail.line"
    _description = "Hotel Room Guest Details"


    partner_id = fields.Many2one("res.partner", string="Guest", ondelete="restrict")

    title = fields.Selection([
        ('Mr', 'Mr'),
        ('Mrs', 'Mrs'),
        ('Ms', 'Ms'),
    ], string="Title")

    first_name = fields.Char("First Name", compute="_compute_fname_lname")
    last_name = fields.Char("Last Name", compute="_compute_fname_lname")

    dob = fields.Date("Date of Birth")

    traveller_type = fields.Selection([
        ('adult', 'Adult'),
        ('child', 'Child')
    ], string="Type", default="adult", compute="_compute_traveller_type")

    room_traveller_line_id = fields.Many2one('hotel.room.traveller.line')

    detail_id = fields.Many2one("hotel.booking.detail", ondelete="cascade")


    @api.depends('partner_id')
    def _compute_fname_lname(self):
        for rec in self:
            if rec.partner_id:
                full_name = rec.partner_id.name or ""
                parts = full_name.split(" ", 1)

                rec.first_name = parts[0]
                rec.last_name = parts[1] if len(parts) > 1 else False
            else:
                rec.first_name = False
                rec.last_name = False


    @api.depends('dob')
    def _compute_traveller_type(self):
        today = date.today()

        for rec in self:
            if rec.dob:
                # Calculate age
                age = today.year - rec.dob.year - ((today.month, today.day) < (rec.dob.month, rec.dob.day))

                # Set traveller type
                if age <= 12:
                    rec.traveller_type = 'child'
                else:
                    rec.traveller_type = 'adult'
            else:
                # No DOB → default to adult
                rec.traveller_type = 'adult'