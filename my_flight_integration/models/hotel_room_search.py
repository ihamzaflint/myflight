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
    ], string="Status", default='draft')

    check_in = fields.Date(string="Check In")
    check_out = fields.Date(string="Check Out")
    country_id = fields.Many2one('res.country', string="Country")
    city_id = fields.Many2one('res.country.city', string="City", domain="[('country_id', '=', country_id)]")
    hotel_ids = fields.Many2many('hotel.booking.line', 'booking_search_hotel_line_rel', 'booking_search_id', 'hotel_id', string="Hotels", domain="[('country_id', '=', country_id), ('city_id', '=', city_id)]")

    line_ids = fields.One2many('hotel.room.search.line', 'hotel_booking_id')

    # Traveller data
    traveller_line_ids = fields.One2many(
        'hotel.room.traveller.line',
        'hotel_room_search_id',
        string="Travellers"
    )

    total_rooms = fields.Integer(compute="_compute_totals", store=True)
    total_adults = fields.Integer(compute="_compute_totals", store=True)
    total_children = fields.Integer(compute="_compute_totals", store=True)

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

        provider = "smart booking"
        hotel_lines = []

        if provider in ["smart booking", "GenX"]:
            hotel_codes = ",".join(self.hotel_ids.mapped("hotel_code"))

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
                    CityCode=self.city_id.code,
                    PaxRooms=pax_rooms
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
                hotel_code = hotel.get("HotelCode")
                rooms = hotel.get("Rooms", {})
                if not rooms:
                    continue

                # If Rooms is a dict, convert to list for uniformity
                if isinstance(rooms, dict):
                    rooms = [rooms]

                for room in rooms:
                    vals = {
                        'name': room.get("Name") or hotel_code,
                        'price': room.get("TotalFare"),
                        'raw_json_data': room,
                        'hotel_booking_id': self.id,
                        'booking_code': room.get("BookingCode"),
                        'meal_type': room.get("MealType"),
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
            # "domain": [("hotel_room_search_id", "=", self.id)],
            # "context": {"default_hotel_room_search_id": self.id},
            "target": "new",
            "view_id": self.env.ref("my_flight_integration.view_hotel_room_search_traveller_add_room_form").id
        }


    @api.model_create_multi
    def create(self, vals_list):
        records = super(HotelRoomSearch, self).create(vals_list)
        for rec in records:
            if not rec.traveller_line_ids:
                rec.write({
                    "traveller_line_ids": [(0, 0, {
                        "adults": 1,
                        "children": 0,
                        "children_ages": ""
                    })]
                })
        return records



class HotelRoomTravellerLine(models.Model):
    _name = "hotel.room.traveller.line"
    _description = "Traveller Details Per Room"

    hotel_room_search_id = fields.Many2one("hotel.room.search", ondelete="cascade")
    # partner_id = fields.Many2one("res.partner", string="Traveller", ondelete="restrict")
    #
    # title = fields.Selection([
    #     ('mr', 'Mr'),
    #     ('mrs', 'Mrs'),
    #     ('ms', 'Ms'),
    #     ('miss', 'Miss')
    # ], string="Title")
    #
    # first_name = fields.Char("First Name")
    # last_name = fields.Char("Last Name")
    #
    # traveller_type = fields.Selection([
    #     ('adult', 'Adult'),
    #     ('child', 'Child')
    # ], string="Type", default="adult")

    adults = fields.Integer("Adults", default=1)
    children = fields.Integer("Children", default=0)
    children_ages = fields.Char("Children Ages", help="Enter ages between 1 and 12. "
             "For multiple ages, use comma-separated values. Example: 5,8,17")


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


class HotelGuestDetailsLine(models.Model):
    _name = "hotel.guest.detail.line"
    _description = "Hotel Room Guest Details"


    partner_id = fields.Many2one("res.partner", string="Guest", ondelete="restrict")

    title = fields.Selection([
        ('mr', 'Mr'),
        ('mrs', 'Mrs'),
        ('ms', 'Ms'),
        ('miss', 'Miss')
    ], string="Title")

    first_name = fields.Char("First Name")
    last_name = fields.Char("Last Name")

    traveller_type = fields.Selection([
        ('adult', 'Adult'),
        ('child', 'Child')
    ], string="Type", default="adult")

    room_traveller_line_id = fields.Many2one('hotel.room.traveller.line')