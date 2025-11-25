from odoo import models, fields
from odoo.exceptions import ValidationError
import html
import logging
_logger = logging.getLogger(__name__)


class HotelBooking(models.Model):
    _name = "hotel.booking"
    _description = "Booking Hotel"
    _inherit = ["hotel.api.service"]
    _rec_name = "country_id"

    country_id = fields.Many2one('res.country', required=True)
    line_ids = fields.One2many('hotel.booking.line', 'hotel_booking_id')

    def action_search_hotels(self):
        """Fetch details for a single hotel using the unified API service"""
        self.ensure_one()
        state_obj = self.env["res.country.city"]
        total_hotel = []

        provider = "smart booking"

        if provider in ["smart booking", "GenX"]:
            try:
                # Fetch hotel codes from API
                data = self.call_hotel_api(provider, "hotel_code_list", CountryCode=self.country_id.code)
            except Exception as e:
                raise ValidationError("Error fetching hotels from API: %s" % e)

            if not data:
                raise ValidationError("No data Found!")

            hotel_list = data.get("HotelList", [])
            if not hotel_list:
                raise ValidationError("No hotels returned for selected country and city.")

            # Remove previous lines before adding fresh data
            self.line_ids.unlink()

            for hotel in hotel_list:
                city_id = state_obj.search([('code', '=', hotel.get('CityCode'))], limit=1)
                vals = {
                    'name': hotel.get('HotelName'),
                    'hotel_code': hotel.get('HotelCode'),
                    'city_id': city_id.id,
                    'country_id': self.country_id.id,
                    'hotel_booking_id': self.id,
                }
                total_hotel.append(vals)

            # Create all records in one batch
            if total_hotel:
                self.env['hotel.booking.line'].create(total_hotel)


class HotelBookingLine(models.Model):
    _name = "hotel.booking.line"
    _description = "Booking Hotel Line"
    _inherit = ["hotel.api.service"]

    name = fields.Char(string="Name")
    hotel_code = fields.Char(string="Hotel Code")
    city_id = fields.Many2one('res.country.city', string="City")
    country_id = fields.Many2one('res.country')
    hotel_booking_id = fields.Many2one('hotel.booking')

    description = fields.Html(string="Description")
    address = fields.Char(string="Address")
    phone = fields.Char(string="Phone")
    fax = fields.Char(string="Fax")
    rating = fields.Char(string="Rating")
    attractions = fields.Text(string="Attractions")
    facilities = fields.Text(string="Facilities")
    images_html = fields.Html("Images")


    def action_fetch_details(self):
        """Fetch details for a single hotel using its hotel_code"""
        self.ensure_one()

        provider = "smart booking"

        if provider in ["smart booking", "GenX"]:
            try:
                data = self.call_hotel_api(provider, "hotel_details", Hotelcodes=self.hotel_code)
            except Exception as e:
                raise ValidationError(f"Error fetching hotel details: {e}")

            hotel_data = data.get("HotelDetails", {})

            # Build HTML for images
            html_images = ""
            for img in hotel_data.get("Images", []):
                html_images += f'<img src="{img}" style="width:150px;height:150px;margin:5px;"/>'

            # Decode description
            raw_description = hotel_data.get("Description")
            description = html.unescape(raw_description) if raw_description else False

            # Save details to hotel record
            self.write({
                'description': description,
                'address': hotel_data.get("Address"),
                'phone': hotel_data.get("PhoneNumber"),
                'fax': hotel_data.get("FaxNumber"),
                'rating': hotel_data.get("HotelRating"),
                'attractions': hotel_data.get("Attractions"),
                'facilities': "\n".join(hotel_data.get("HotelFacilities", [])),
                'images_html': html_images
            })