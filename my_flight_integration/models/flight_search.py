from odoo import models, fields, api
from datetime import date
import json
import requests
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class FlightSearch(models.Model):
    _name = "flight.search"
    _description = "Flight Search"
    _rec_name = "display_name"

    display_name = fields.Char(string="Display Name", compute="_compute_display_name", store=True)

    @api.depends('travel_date', 'origin_id', 'destination_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.origin_id and rec.destination_id:
                rec.display_name = f"Flight Booking [{rec.origin_id.city} → {rec.destination_id.city}]"
            else:
                rec.display_name = "Booking"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('searched', 'Searched'),
        ('result_found', 'Result Found'),
        ('not_found', 'Result Not Found'),
        ('booked', 'Booked')
    ], string="Status", default='draft')

    origin_id = fields.Many2one('iata.code')
    destination_id = fields.Many2one('iata.code')
    travel_date = fields.Date(string="Date")
    flight_search_line_ids = fields.One2many('flight.search.line', 'flight_search_id')
    direct_flight = fields.Boolean(string="Direct Flight?")
    adults = fields.Integer("Adults", default=1)
    children = fields.Integer("Children(0 to 12y)")
    held_infant = fields.Integer("Held Infant(0 to 2y)")
    seated_infant = fields.Integer("Seated Infant(0 to 2y)")
    cabin_class = fields.Selection([
        ('ECONOMY', 'ECONOMY'),
        ('PREMIUM_ECONOMY', 'PREMIUM_ECONOMY'),
        ('BUSINESS', 'BUSINESS'),
        ('FIRST', 'FIRST'),
    ], string="Class", default='ECONOMY', required=True)
    ticket_counts = fields.Char("ticket", compute='_compute_ticket_count')
    trip_type = fields.Selection([
        ('oneway', 'OneWay'),
        ('return', 'Return'),
    ], string="TripType", default='oneway', required=True)
    travel_return_date = fields.Date(string="Return")
    flight_stop_ids = fields.Many2many('flight.stop', 'booking_search_flight_stop_rel', 'flight_search_id',
                                       'flight_stop_id')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self._default_currency_id())

    def _default_currency_id(self):
        return self.env.user.company_id.currency_id


    @api.onchange('trip_type')
    def _onchange_return_date(self):
        for rec in self:
            if rec.trip_type and rec.trip_type == 'oneway':
                rec.travel_return_date = False

    @api.constrains('adults', 'children', 'held_infant', 'seated_infant')
    def _check_travel_rules(self):
        for rec in self:
            adults = rec.adults or 0
            children = rec.children or 0
            held_infant = rec.held_infant or 0
            seated_infant = rec.seated_infant or 0

            total_infants = held_infant + seated_infant

            # 1. At least 1 adult required always
            if adults < 1:
                raise ValidationError("At least 1 adult must be entered.")

            # 2. Child cannot travel without an adult
            if children > 0 and adults < 1:
                raise ValidationError("Children cannot travel without at least 1 adult.")

            # 3. Per adult only one infant
            if total_infants > adults:
                raise ValidationError(
                    "Each infant must be accompanied by one adult. "
                    "Infants cannot exceed number of adults."
                )

    def _compute_ticket_count(self):
        for rec in self:
            ticket = "Adults(%s) Children(%s) %s" %(str(rec.adults), str(rec.children), str(rec.cabin_class))
            rec.ticket_counts = ticket

    @api.constrains('origin_id', 'destination_id')
    def _check_different_locations(self):
        for rec in self:
            if rec.origin_id and rec.destination_id and rec.origin_id.id == rec.destination_id.id:
                raise ValidationError("Origin and Destination cannot be the same.")

    @api.constrains('travel_date')
    def restrict_travel_date(self):
        for rec in self:
            if rec.travel_date and rec.travel_date < date.today():
                raise ValidationError("Date is a past date.")

    def _convert_duration(self, duration_input):
        """Convert single or multiple ISO durations (PT5H15M)
        into formatted text like: '2 hours 15 minutes | 3 hours 35 minutes'."""

        def parse_single(d):
            """Parse a single PT-duration string to 'X hours Y minutes'."""
            if not d:
                return "-"

            d = d.replace("PT", "")
            hours = 0
            minutes = 0

            if "H" in d:
                parts = d.split("H")
                hours = int(parts[0]) if parts[0] else 0
                d = parts[1] if len(parts) > 1 else ""

            if "M" in d:
                minutes = int(d.replace("M", "") or 0)

            # Build text
            hour_str = f"{hours} hour{'s' if hours != 1 else ''}" if hours else ""
            minute_str = f"{minutes} minute{'s' if minutes != 1 else ''}" if minutes else ""

            return (hour_str + " " + minute_str).strip() or "-"

        # Normalize to list
        if isinstance(duration_input, str):
            duration_list = [duration_input]
        else:
            duration_list = duration_input or []

        # Convert each duration separately
        formatted_durations = [parse_single(d) for d in duration_list]

        # Join with " | "
        return " | ".join(formatted_durations)

    def action_search_flight(self):
        api_service = self.env['flight.api.service'].sudo()
        for rec in self:
            flight_conf = self.env.ref('my_flight_integration.booking_conf_flight').sudo()
            print("flight_conf????????????/", flight_conf.line_ids)
            new_results = []
            total_results = 0
            if flight_conf and flight_conf.line_ids:
                for line in flight_conf.line_ids:
                    end_point = ''
                    if line.code == 'amadeus':
                        end_point = '/shopping/flight-offers'
                    body = api_service._prepare_body(rec, line, service_provider=line.code, end_point=end_point)
                    if body:
                        data = api_service.call_api(
                            api_type=line.code,
                            endpoint=end_point,
                            flight_search_id=rec.id,
                            payload=body,
                            version='v2'
                        )
                        data = data.json()
                        if not data:
                            continue
                        if line.code == 'amadeus':
                            found_flights, total_result_count = api_service.response_manager(response=data, api_type=line.code, booking_rec=rec, endpoint=end_point)
                            new_results = new_results + found_flights
                            total_results = total_results + total_result_count
                self.flight_search_line_ids.unlink()
                if new_results:
                    for vals in new_results:
                        # Create a line for each flight offer
                        self.flight_search_line_ids.create(vals)
                    self.state = 'result_found'
                else:
                    self.state = 'not_found'

            else:
                raise ValidationError("No flight API configuration found in Booking Configuration.")
