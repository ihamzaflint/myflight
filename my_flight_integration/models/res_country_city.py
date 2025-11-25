from odoo import models, fields
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


class ResCountryStateCity(models.Model):
    _name = "res.country.city"
    _description = "State City"
    _inherit = ["hotel.api.service"]

    name = fields.Char()
    code = fields.Char()
    country_id = fields.Many2one('res.country', string="Country")


    def cron_fetch_all_cities_from_api(self):
        """Scheduled job: fetch cities for all countries in the predefined list"""
        country_codes = [
            "AF","AL","DZ","AS","AD","AO","AI","AQ","AG","AR","AM","AW","AU","AT","AZ","BS","BH","BD","BB",
            "BY","BE","BZ","BJ","BM","BT","BO","BQ","BA","BW","BV","BR","BC","BN","BG","BF","BI","KH","CM",
            "CA","CV","KY","CF","TD","CL","CN","CX","CC","CO","KM","CG","CD","CK","CR","CT","HR","CU","CY",
            "CZ","DK","DJ","DM","DO","EO","EC","EG","SV","GQ","ER","EE","ET","EP","FK","FO","FJ","FI","FR",
            "GF","PF","FT","GA","GM","GE","DE","GH","GI","GR","GL","GD","GP","GU","GT","GN","GW","GY","HT",
            "HW","HI","HN","HK","HU","IS","IN","ID","IR","IQ","IE","IL","IT","CI","JM","JP","JE","JO","KZ",
            "KE","KI","KP","KV","KW","KG","LA","LV","LB","LS","LR","LY","LI","LT","LU","MO","MK","MG","MW",
            "MY","MV","ML","MT","MH","MQ","MR","MU","YT","MX","FM","MD","MC","MN","ME","MS","MA","MZ","MM",
            "NA","NR","NP","NL","AN","NC","NZ","NI","NE","NG","NU","NF","NK","MP","NO","OM","PK","PW","PS",
            "PA","PG","PY","PE","PH","PC","PL","PT","PR","QA","RE","RO","RU","RW","SW","KN","LC","SJ","MF",
            "WS","SM","ST","SA","SN","RS","SC","SL","SG","SK","SI","SB","SO","ZA","KR","ES","LK","VC","SH",
            "PM","SD","SR","SP","SZ","SE","CH","SY","TW","TJ","TZ","TH","TG","TK","TO","TT","TN","TR","TM",
            "TC","TV","VI","UG","UA","AE","GB","UK","UY","US","UZ","VU","VE","VN","VG","WF","WR","YE","ZR",
            "ZM","ZW"
        ]

        for code in country_codes:
            name = COUNTRY_DATA.get(code)
            country = self.env["res.country"].search([
                "|",("code", "=", code),("name", "=", name)
            ], limit=1)

            if country:
                country.write({
                    "code": code,
                })

            else:
                country = self.env["res.country"].create({
                    "name": COUNTRY_DATA.get(code),
                    "code": code,
                })
                _logger.info(f"Created missing country: {code}")

            try:
                data = self.call_hotel_api("smart booking", "city_list", CountryCode=country.code)
            except Exception as e:
                _logger.error(f"API error while fetching cities for {country.code}: {e}")
                continue

            city_list = data.get("CityList", [])
            if isinstance(city_list, dict):
                city_list = [city_list]


            if not city_list:
                _logger.warning(f"No cities returned for country: {country.code}")
                continue

            if data.get("Status").get("Code") == '200':
                for city in city_list:
                    vals = {
                        "name": city.get("CityName"),
                        "code": city.get("CityCode"),
                        "country_id": country.id
                    }

                    existing = self.search([
                        ("code", "=", city.get("CityCode")),
                        ("country_id", "=", country.id)
                    ], limit=1)

                    if existing:
                        existing.write(vals)
                    else:
                        self.create(vals)

        _logger.info("City sync completed for all country codes.")