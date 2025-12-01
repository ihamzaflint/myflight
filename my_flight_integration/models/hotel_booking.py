from odoo import models, fields
from odoo.exceptions import ValidationError
import html
import logging
_logger = logging.getLogger(__name__)

COUNTRY_DATA = {
    "AF": "Afghanistan",        "AL": "Albania",                 "DZ": "Algeria",
    "AS": "American Samoa",     "AD": "Andorra",                 "AO": "Angola",
    "AI": "Anguilla",           "AQ": "Antarctica",              "AG": "Antigua",
    "AR": "Argentina",          "AM": "Armenia",                 "AW": "Aruba",
    "AU": "Australia",          "AT": "Austria",                 "AZ": "Azerbaijan",
    "BS": "Bahamas",            "BH": "Bahrain",                 "BD": "Bangladesh",
    "BB": "Barbados",           "BY": "Belarus",                 "BE": "Belgium",
    "BZ": "Belize",             "BJ": "Benin",                   "BM": "Bermuda",
    "BT": "Bhutan",             "BO": "Bolivia",                 "BQ": "Bonaire",
    "BA": "Bosnia",             "BW": "Botswana",                "BV": "Bouvet Island",
    "BR": "Brazil",             "BC": "British Indian Ocean Territory", "BN": "Brunei Darussalam",
    "BG": "Bulgaria",           "BF": "Burkina Faso",            "BI": "Burundi",
    "KH": "Cambodia",           "CM": "Cameroon",                "CA": "Canada",
    "CV": "Cape Verde",         "KY": "Cayman (Islands)",        "CF": "Central African Republic",
    "TD": "Chad",               "CL": "Chile",                   "CN": "China",
    "CX": "Christmas Island",   "CC": "Cocos (Keeling) Islands", "CO": "Colombia",
    "KM": "Comoros",            "CG": "Congo",                   "CD": "Congo (Rep. Dem.)",
    "CK": "Cook Islands",       "CR": "Costa Rica",              "CT": "Cote D'Ivoire",
    "HR": "Croatia",            "CU": "Cuba",                    "CY": "Cyprus",
    "CZ": "Czech Republic",     "DK": "Denmark",                 "DJ": "Djibouti",
    "DM": "Dominica",           "DO": "Dominican Republic",      "EO": "East Timor",
    "EC": "Ecuador",            "EG": "Egypt",                   "SV": "El Salvador",
    "GQ": "Equatorial Guinea",  "ER": "Eritrea",                 "EE": "Estonia",
    "ET": "Ethiopia",           "EP": "Europe Community",        "FK": "Falkland Islands",
    "FO": "Faroe Islands",      "FJ": "Fiji",                    "FI": "Finland",
    "FR": "France",             "GF": "French Guiana",           "PF": "French Polynesia",
    "FT": "French Southern Territories", "GA": "Gabon",          "GM": "Gambia",
    "GE": "Georgia",            "DE": "Germany",                 "GH": "Ghana",
    "GI": "Gibraltar",          "GR": "Greece",                  "GL": "Greenland",
    "GD": "Grenada",            "GP": "Guadeloupe",              "GU": "Guam",
    "GT": "Guatemala",          "GN": "Guinea",                  "GW": "Guinea-Bissau",
    "GY": "Guyana",             "HT": "Haiti",                   "HW": "Hawaii",
    "HI": "Heard And Mc Donald Islands", "HN": "Honduras",       "HK": "Hong Kong",
    "HU": "Hungary",            "IS": "Iceland",                 "IN": "India",
    "ID": "Indonesia",          "IR": "Iran",                    "IQ": "Iraq",
    "IE": "Ireland",            "IL": "Israel",                  "IT": "Italy",
    "CI": "Ivory Coast",        "JM": "Jamaica",                 "JP": "Japan",
    "JE": "Jersey",             "JO": "Jordan",                  "KZ": "Kazakhstan",
    "KE": "Kenya",              "KI": "Kiribati",                "KP": "Korea Republic Of",
    "KV": "Kosovo",             "KW": "Kuwait",                  "KG": "Kyrgyzstan",
    "LA": "Laos",               "LV": "Latvia",                  "LB": "Lebanon",
    "LS": "Lesotho",            "LR": "Liberia",                 "LY": "Libya",
    "LI": "Liechtenstein",      "LT": "Lithuania",               "LU": "Luxembourg",
    "MO": "Macau",              "MK": "Macedonia",               "MG": "Madagascar",
    "MW": "Malawi",             "MY": "Malaysia",                "MV": "Maldives",
    "ML": "Mali",               "MT": "Malta",                   "MH": "Marshall Islands",
    "MQ": "Martinique",         "MR": "Mauritania",              "MU": "Mauritius",
    "YT": "Mayotte",            "MX": "Mexico",                  "FM": "Micronesia",
    "MD": "Moldova",            "MC": "Monaco",                  "MN": "Mongolia",
    "ME": "Montenegro",         "MS": "Montserrat",              "MA": "Morocco",
    "MZ": "Mozambique",         "MM": "Myanmar",                 "NA": "Namibia",
    "NR": "Nauru",              "NP": "Nepal",                   "NL": "Netherlands",
    "AN": "Netherlands Antilles", "NC": "New Caledonia",         "NZ": "New Zealand",
    "NI": "Nicaragua",          "NE": "Niger",                   "NG": "Nigeria",
    "NU": "Niue",               "NF": "Norfolk Island",          "NK": "North Korea",
    "MP": "Northern Mariana Island", "NO": "Norway",             "OM": "Oman",
    "PK": "Pakistan",           "PW": "Palau",                   "PS": "Palestine",
    "PA": "Panama",             "PG": "Papua New Guinea",        "PY": "Paraguay",
    "PE": "Peru",               "PH": "Philippines",             "PC": "Pitcairn",
    "PL": "Poland",             "PT": "Portugal",                "PR": "Puerto Rico",
    "QA": "Qatar",              "RE": "Reunion",                 "RO": "Romania",
    "RU": "Russia",             "RW": "Rwanda",                  "SW": "Saint Barthelemy",
    "KN": "Saint Kitts And Nevis", "LC": "Saint Lucia",          "SJ": "Saint Marteen",
    "MF": "Saint Martin",       "WS": "Samoa",                   "SM": "San Marino",
    "ST": "Sao Tome And Principe", "SA": "Saudi Arabia",         "SN": "Senegal",
    "RS": "Serbia",             "SC": "Seychelles",              "SL": "Sierra Leone",
    "SG": "Singapore",          "SK": "Slovakia",                "SI": "Slovenia",
    "SB": "Solomon Islands",    "SO": "Somalia",                 "ZA": "South Africa",
    "KR": "South Korea",        "ES": "Spain",                   "LK": "Sri Lanka",
    "VC": "St Vincent & Grenadines", "SH": "St. Helena",         "PM": "St. Pierre And Miquelon",
    "SD": "Sudan",              "SR": "Suriname",                "SP": "Svalbard And Jan Mayen Islands",
    "SZ": "Swaziland",          "SE": "Sweden",                  "CH": "Switzerland",
    "SY": "Syria",              "TW": "Taiwan",                  "TJ": "Tajikistan",
    "TZ": "Tanzania",           "TH": "Thailand",                "TG": "Togo",
    "TK": "Tokelau",            "TO": "Tonga",                   "TT": "Trinidad And Tobago",
    "TN": "Tunisia",            "TR": "Turkey",                  "TM": "Turkmenistan",
    "TC": "Turks And Caicos",   "TV": "Tuvalu",                  "VI": "U.S. Virgin Islands",
    "UG": "Uganda",             "UA": "Ukraine",                 "AE": "United Arab Emirates",
    "GB": "United Kingdom",     "UK": "United Kingdom",          "UY": "Uruguay",
    "US": "USA",                "UZ": "Uzbekistan",              "VU": "Vanuatu",
    "VE": "Venezuela",          "VN": "Vietnam",                 "VG": "Virgin Islands (British)",
    "WF": "Wallis And Futuna Islands", "WR": "Western Sahara",   "YE": "Yemen",
    "ZR": "Zaire",              "ZM": "Zambia",                  "ZW": "Zimbabwe",
}




class HotelBooking(models.Model):
    _name = "hotel.booking"
    _description = "Booking Hotel"
    _inherit = ["hotel.api.service"]
    _rec_name = "country_id"

    country_id = fields.Many2one('res.country', required=True)
    line_ids = fields.One2many('hotel.booking.line', 'hotel_booking_id')

    def action_update_hotels(self):
        """Fetch + Sync hotels for selected country using GenX provider."""
        self.ensure_one()

        City = self.env["res.country.city"]
        HotelLine = self.env["hotel.booking.line"]

        provider = "GenX"

        # ----------------------------------------------------------------------
        # 1. Get API Response
        # ----------------------------------------------------------------------
        try:
            data = self.call_hotel_api(provider, "hotel_code_list", CountryCode=self.country_id.code)
        except Exception as e:
            raise ValidationError("API error: %s" % e)

        hotel_list = data.get("HotelList", [])
        if not hotel_list:
            raise ValidationError("No hotels returned from API.")

        # Convert API hotels → dict for fast lookup
        api_hotel_map = {
            h["HotelCode"]: h
            for h in hotel_list
        }
        api_codes = set(api_hotel_map.keys())


        # ----------------------------------------------------------------------
        # 2. Get existing hotels (INCLUDING inactive ones)
        # ----------------------------------------------------------------------
        existing_hotels = HotelLine.search([
            ("country_id", "=", self.country_id.id)
        ])

        existing_map = {h.code: h for h in existing_hotels}

        create_vals = []
        update_vals = {}

        # ----------------------------------------------------------------------
        # 3. Process API hotels → create or update
        # ----------------------------------------------------------------------
        for code, api_hotel in api_hotel_map.items():

            city = City.search([("code", "=", api_hotel.get("CityCode"))], limit=1)

            if code in existing_map:
                # Already exists → update details
                update_vals[existing_map[code]] = {
                    "name": api_hotel.get("HotelName"),
                    "city_id": city.id if city else False,
                    "active": True,
                }
            else:
                # Not exists → create new hotel
                create_vals.append({
                    "name": api_hotel["HotelName"],
                    "code": code,
                    "city_id": city.id if city else False,
                    "country_id": self.country_id.id,
                    "hotel_booking_id": self.id,
                })

        # ----------------------------------------------------------------------
        # 4. Create new hotels
        # ----------------------------------------------------------------------
        if create_vals:
            HotelLine.create(create_vals)


        # ----------------------------------------------------------------------
        # 5. Update existing hotels
        # ----------------------------------------------------------------------
        for hid, vals in update_vals.items():
            hid.write(vals)

        # ----------------------------------------------------------------------
        # 6. Deactivate hotels NOT returned in API
        # ----------------------------------------------------------------------
        inactive = existing_hotels.filtered(lambda h: h.code not in api_codes)
        inactive.write({"active": False})

        return True



    def cron_fetch_hotel_data(self):
        """
        Fetch hotel list from provider for ALL countries.
        Update/Create/Deactivate hotels.
        """

        country_codes = COUNTRY_DATA.keys()

        # country_codes = [
        #     "DZ"
        # ]
        Country = self.env["res.country"]
        HotelLine = self.env["hotel.booking.line"]
        City = self.env["res.country.city"]
        provider = "GenX"

        if provider in ["GenX"]:

            for country_code in country_codes:
                try:
                    # Fetch hotel codes from API
                    data = self.call_hotel_api(provider, "hotel_code_list", CountryCode=country_code)
                except Exception as e:
                    raise ValidationError("Error fetching hotels from API: %s" % e)

                if not data:
                    raise ValidationError("No data Found!")

                hotel_list = data.get("HotelList", [])
                if not hotel_list:
                    _logger.warning(f"No hotels returned for {country_code}")
                    continue


                # Convert list → dict by HotelCode for quick lookup
                api_hotel_codes = {hotel['HotelCode']: hotel for hotel in hotel_list}

                # fetch existing hotels in DB for this country
                existing_hotels = HotelLine.search([("country_id.code", "=", country_code)])
                existing_hotel_map = {h.code: h for h in existing_hotels}

                create_vals = []
                update_vals = {}
                active_api_codes = set(api_hotel_codes.keys())


                # -------------------------
                # 1. Create or Update Hotels
                # -------------------------
                for hotel_code, data_hotel in api_hotel_codes.items():
                    city = City.search([("code", "=", data_hotel.get("CityCode"))], limit=1)

                    if hotel_code in existing_hotel_map:
                        # Prepare write values
                        update_vals[existing_hotel_map[hotel_code].id] = {
                            "name": data_hotel.get("HotelName"),
                            "city_id": city.id if city else False,
                            "active": True,
                        }
                    else:
                        # Find existing hotel.booking for this country
                        booking = self.search([('country_id.code', '=', country_code)], limit=1)

                        if not booking:
                            # Create master booking record if not exists
                            country_rec = Country.search([('code', '=', country_code)], limit=1)
                            booking = self.create({
                                "country_id": country_rec.id,
                            })

                        # Now prepare hotel booking line
                        create_vals.append({
                            "name": data_hotel.get("HotelName"),
                            "code": hotel_code,
                            "city_id": city.id if city else False,
                            "country_id": booking.country_id.id,
                            "hotel_booking_id": booking.id,
                        })


                # Update hotels in batch
                for hotel_line_id, vals in update_vals.items():
                    hotel_obj = HotelLine.browse(hotel_line_id)
                    hotel_obj.write(vals)

                # Create hotels in batch
                if create_vals:
                    HotelLine.create(create_vals)


                # -------------------------
                # 2. Deactivate Hotels NOT returned by API
                # -------------------------
                inactive_hotels = existing_hotels.filtered(
                    lambda h: h.code not in active_api_codes
                )
                inactive_hotels.write({"active": False})

                _logger.info(
                    f"Country {country_code}: Created {len(create_vals)}, "
                    f"Updated {len(update_vals)}, "
                    f"Deactivated {len(inactive_hotels)} hotels."
                )



class HotelBookingLine(models.Model):
    _name = "hotel.booking.line"
    _description = "Booking Hotel Line"
    _inherit = ["hotel.api.service"]

    name = fields.Char(string="Name")
    active = fields.Boolean("Active", default=True)
    code = fields.Char(string="Hotel Code")
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


        provider = "GenX"
        if provider in ["GenX"]:
            try:
                data = self.call_hotel_api(provider, "hotel_details", Hotelcodes=self.code)
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