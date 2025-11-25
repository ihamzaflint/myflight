import requests
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
import json


class FlightApiService(models.AbstractModel):
    _name = 'flight.api.service'
    _description = 'Flight API Services'

    @api.model
    def common_get_config(self, api_type):
        """Fetch API configuration for given type."""
        config = self.env['booking.conf.line'].search([
            ('name', '=', api_type),
        ], limit=1)
        if not config:
            raise UserError(_("No active configuration found for API type: %s") % api_type)
        return config

    @api.model
    def get_log_type(self, response):
        log_type = 'warning'
        if response.status_code in (401, 403, 500, 400):
            log_type = 'error'

        if response.status_code == 200:
            log_type = 'success'
        return log_type

    @api.model
    def common_get_header(self, config):
        header = {}
        if config.name == 'amadeus':
            header['Authorization'] = f"Bearer {config.access_token}"
        return header

    @api.model
    def common_get_required_payload(self, config, payload):
        if config.name == 'amadeus':
            payload['grant_type'] = 'client_credentials'
        return payload

    @api.model
    def common_get_token(self, config, flight_search_id=None):
        book_id = flight_search_id
        payload = {}
        if config.name == 'amadeus':
            auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
            # auth_url = f"{config.url.rstrip('/')}/security/oauth2/token"
            payload = {
                "grant_type": "client_credentials",
                "client_id": config.username,
                "client_secret": config.password
            }
        self.store_log(name='', log_type=None, type='request', url=auth_url,
                       code=None, status=None, title=None, detail=None,
                       reference=None, provider_id=config.id, flight_search_id=book_id, flight_search_line_id=None,
                       request_payload=payload, response_payload=None, request_date=fields.Datetime.now()
                       )
        response = requests.post(auth_url, data=payload)
        log_type = self.get_log_type(response)
        self.store_log(name='', log_type=log_type, type='response', url=auth_url,
                       code=response.status_code, status=None, title=None, detail=None,
                       reference=None, provider_id=config.id, flight_search_id=book_id, flight_search_line_id=None,
                       request_payload=payload, response_payload=response.json(),
                       request_date=fields.Datetime.now()
                       )
        return response

    @api.model
    def common_refresh_token(self, api_type, flight_search_id=None):
        """Generic token refresh handler."""
        config = self.common_get_config(api_type)
        book_id = flight_search_id

        if not (config.username and config.password):
            raise UserError(_("Username/Password missing for %s") % api_type)

        response = self.common_get_token(config, flight_search_id=book_id)

        if response.status_code == 200:
            data = response.json()
            new_token = data.get('access_token')
            if not new_token:
                raise UserError(_("No access_token returned during refresh for %s") % api_type)
            config.access_token = new_token
        else:
            raise UserError(f"Token refresh failed for {api_type}: {response.text}")

    @api.model
    def store_log(self, name=None, log_type=None, type=None, url=None,
                  code=None, status=None, title=None, detail=None,
                  reference=None, provider_id=None, flight_search_id=None, flight_search_line_id=None,
                  request_payload=None, response_payload=None, request_date=None
                  ):
        log = self.env['flight.api.log'].sudo()
        booking_conf_line = self.env['booking.conf.line'].sudo()
        data = {}
        is_error_response = False
        if response_payload and provider_id:
            if response_payload.get("errors",False):
                is_error_response = True
                booking_conf_line = booking_conf_line.browse([provider_id])

        if booking_conf_line.name == 'amadeus' and is_error_response:
            for err in response_payload["errors"]:
                code = err.get("code", "")
                title = err.get("title", "")
                detail = err.get("detail", "")
                log_type = 'error'
                type = 'error'
                status = err.get("code", "")
                log.create({
                    'code':code,
                    'title':title,
                    'detail':detail,
                    'type':log_type,
                    'status':status,
                })
            return True
        # else:
        if name:
            data['name'] = name
        if log_type:
            data['log_type'] = log_type
        if type:
            data['type'] = type
        if url:
            data['url'] = url
        if code:
            data['code'] = code
        if status:
            data['status'] = status
        if title:
            data['title'] = title
        if detail:
            data['detail'] = detail
        if reference:
            data['reference'] = reference
        if provider_id:
            data['provider_id'] = provider_id
        if flight_search_id:
            data['flight_search_id'] = flight_search_id
        if flight_search_line_id:
            data['flight_search_line_id'] = flight_search_line_id
        if request_payload:
            data['request_payload'] = request_payload
        if response_payload:
            data['response_payload'] = response_payload
        if request_date:
            data['request_date'] = request_date

        log.create(data)
        return True

    @api.model
    def call_api(self, api_type, endpoint, flight_search_id, payload=None, method='POST', headers=None, retry=False, version=''):
        """Call API using stored configuration."""
        config = self.common_get_config(api_type)
        url = ''
        if version:
            url = f"{config.url.rstrip('/')}/{version}/{endpoint.lstrip('/')}"
        else:
            url = f"{config.url.rstrip('/')}/{endpoint.lstrip('/')}"
        default_headers = self.common_get_header(config)

        if headers:
            default_headers.update(headers)
        self.common_get_required_payload(config, payload)
        try:
            self.store_log(name='', log_type=None, type='request', url=url,
                           code=None, status=None, title=None, detail=None,
                           reference=None, provider_id=config.id, flight_search_id=flight_search_id, flight_search_line_id=None,
                           request_payload=payload, response_payload=None, request_date=fields.Datetime.now()
                           )
            # url = 'https://test.api.amadeus.com/v1/shopping/flight-offers/pricing'
            response = requests.request(method, url, json=payload, headers=default_headers)


            log_type = self.get_log_type(response)
            self.store_log(name='', log_type=log_type, type='response', url=url,
                           code=response.status_code, status=None, title=None, detail=None,
                           reference=None, provider_id=config.id, flight_search_id=flight_search_id, flight_search_line_id=None,
                           request_payload=payload, response_payload=response.json(), request_date=fields.Datetime.now()
                           )
            if response.status_code in (401, 403) and not retry:
                # Try refreshing token if credentials exist
                if config.username and config.password:
                    self.common_refresh_token(api_type, flight_search_id=flight_search_id)
                    return self.call_api(api_type, endpoint, flight_search_id, payload, method, headers, retry=True,
                                         version=version)
                else:
                    raise UserError(_("[%s] Access token missing or invalid, and credentials not set.") % api_type)

            if response.status_code == 201:
                log_type = self.get_log_type(response)
                # raise UserError(f"[{api_type.upper()}] API call failed: {response.status_code} - {response.text}")
                self.store_log(name='', log_type=log_type, type='response', url=url,
                               code=response.status_code, status=None, title=None, detail=None,
                               reference=None, provider_id=config.id, flight_search_id=flight_search_id, flight_search_line_id=None,
                               request_payload=payload, response_payload=response.json(),
                               request_date=fields.Datetime.now()
                               )
                return response

            if response.status_code != 200:
                log_type = self.get_log_type(response)
                # raise UserError(f"[{api_type.upper()}] API call failed: {response.status_code} - {response.text}")
                self.store_log(name='', log_type=log_type, type='response', url=url,
                               code=response.status_code, status=None, title=None, detail=None,
                               reference=None, provider_id=config.id, flight_search_id=flight_search_id, flight_search_line_id=None,
                               request_payload=payload, response_payload=response.json(),
                               request_date=fields.Datetime.now()
                               )
                return response
            if response.status_code:
                log_type = self.get_log_type(response)
                # raise UserError(f"[{api_type.upper()}] API call failed: {response.status_code} - {response.text}")
                self.store_log(name='', log_type=log_type, type='response', url=url,
                               code=response.status_code, status=None, title=None, detail=None,
                               reference=None, provider_id=config.id, flight_search_id=flight_search_id,
                               flight_search_line_id=None,
                               request_payload=payload, response_payload=response.json(),
                               request_date=fields.Datetime.now()
                               )

            return response
        except Exception as e:
            raise UserError(f"Error while calling {api_type.upper()} API: {str(e)}")

    @api.model
    def response_manager(self, response=None, api_type=None, booking_rec=None, endpoint=None):
        booking_id = booking_rec
        if not response or not api_type:
            return [], 0

        api_type = api_type.lower()

        if api_type == "amadeus":
            if endpoint == '/shopping/flight-offers':
                if not response or not api_type:
                    return [], 0
                total_flight = []
                total_results = 0
                selected_stops = booking_id.flight_stop_ids.mapped('value')
                stop_filter_enabled = bool(selected_stops)

                config = self.common_get_config("amadeus")

                offers = response.get("data", [])
                if not offers:
                    booking_id.state = 'not_found'
                    raise ValidationError("No Data Found!")

                for offer in offers:
                    itineraries = offer.get("itineraries", [])
                    if not itineraries:
                        continue

                    total_duration = [it.get("duration", "-") for it in itineraries]
                    # total_duration = itineraries[0].get("duration", "-")
                    all_segments_info = []
                    total_stops = 0

                    for itinerary in itineraries:
                        segments = itinerary.get("segments", [])
                        stops = max(len(segments) - 1, 0)

                        total_stops += stops

                        # Build route text
                        route_list = []
                        for seg in segments:
                            dep = seg["departure"]["iataCode"]
                            dep_time = seg["departure"]["at"]
                            arr = seg["arrival"]["iataCode"]
                            arr_time = seg["arrival"]["at"]
                            route_list.append(f"{dep} ({dep_time}) → {arr} ({arr_time})")

                        all_segments_info.append(" → ".join(route_list))

                    if stop_filter_enabled and total_stops not in selected_stops:
                        continue

                    full_route = " | ".join(all_segments_info)
                    airline = offer.get("validatingAirlineCodes", ["-"])[0]
                    carrier_name = response.get("dictionaries", {}).get("carriers", {}).get(airline, airline)
                    duration = booking_id._convert_duration(total_duration)

                    total_flight.append({
                        "name": f"✈ {carrier_name}",
                        "price": offer.get("price", {}).get("total", "0.00"),
                        "location": full_route,
                        "stops": total_stops,
                        "duration": duration,
                        "flight_search_id": booking_id.id,
                        "raw_json_data": json.dumps(offer),
                        "conf_id": config.id,
                    })

                    total_results += 1

                return total_flight, total_results

    @api.model
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

    @api.model
    def _prepare_body(self, flight_search_id, line, service_provider=None, end_point=None):
        if not (line and service_provider):
            return {}

        if service_provider == 'amadeus':

            # -----------------------------
            # 1. Build traveler list
            # -----------------------------
            if end_point == '/shopping/flight-offers':
                travelers = []
                traveler_id = 1

                adult_ids = []
                for _ in range(flight_search_id.adults):
                    travelers.append({
                        "id": str(traveler_id),
                        "travelerType": "ADULT"
                    })
                    adult_ids.append(str(traveler_id))
                    traveler_id += 1

                for _ in range(flight_search_id.children):
                    travelers.append({
                        "id": str(traveler_id),
                        "travelerType": "CHILD"
                    })
                    traveler_id += 1

                for _ in range(flight_search_id.seated_infant):
                    travelers.append({
                        "id": str(traveler_id),
                        "travelerType": "SEATED_INFANT"
                    })
                    traveler_id += 1

                for index in range(flight_search_id.held_infant):
                    # pick adult by index (adult_ids[0], adult_ids[1], ...)
                    associated_adult = adult_ids[index]

                    travelers.append({
                        "id": str(traveler_id),
                        "travelerType": "HELD_INFANT",
                        "associatedAdultId": associated_adult
                    })
                    traveler_id += 1

                # -----------------------------
                # 2. Build origin-destination segment
                # -----------------------------
                origin_destinations = [{
                    "id": "1",
                    "originLocationCode": flight_search_id.origin_id.code,
                    "destinationLocationCode": flight_search_id.destination_id.code,
                    "departureDateTimeRange": {
                        "date": str(flight_search_id.travel_date)
                    }
                }]

                if flight_search_id.trip_type == 'return' and flight_search_id.travel_return_date:
                    origin_destinations.append({
                        "id": "2",
                        "originLocationCode": flight_search_id.destination_id.code,
                        "destinationLocationCode": flight_search_id.origin_id.code,
                        "departureDateTimeRange": {
                            "date": str(flight_search_id.travel_return_date)
                        }
                    })

                # -----------------------------
                # 3. Build search criteria
                # -----------------------------
                search_criteria = {
                    "maxFlightOffers": 250,
                    "flightFilters": {
                        "cabinRestrictions": [
                            {
                                "cabin": flight_search_id.cabin_class,  # Dynamic cabin
                                "coverage": "MOST_SEGMENTS",
                                "originDestinationIds": ["1"]
                            }
                        ],
                        "carrierRestrictions": {}
                    }
                }

                # Apply direct flight filter
                if flight_search_id.direct_flight:
                    search_criteria["flightFilters"]["nonStop"] = False

                # -----------------------------
                # 4. Build final body
                # -----------------------------
                body = {
                    "currencyCode": self.env.company.currency_id.name or "USD",
                    "originDestinations": origin_destinations,
                    "travelers": travelers,
                    "sources": ["GDS"],
                    "searchCriteria": search_criteria
                }
                return body
            elif end_point == '/shopping/flight-offers/pricing':
                body = {
                    "data": {
                        "type": "flight-offers-pricing",
                        "flightOffers": [json.loads(line.raw_json_data)]
                    }
                }
                return body
            elif end_point == '/booking/flight-orders':
                travellers_payload = []
                contacts_payload = []
                travel_count = 0
                for traveller in line.travellers_ids:
                    travel_count += 1
                    mobile_number = traveller.mobile
                    phone = traveller.phone
                    traveller_country = traveller.traveller_country_id
                    phone_entry = []
                    if mobile_number:
                        phone_entry.append({
                            "deviceType": "MOBILE",
                            "countryCallingCode": str(traveller_country.phone_code) if traveller_country else "",
                            "number": mobile_number
                        })
                    if phone:
                        phone_entry.append({
                            "deviceType": "LANDLINE",
                            "countryCallingCode": str(traveller_country.phone_code) if traveller_country else "",
                            "number": phone
                        })
                    # ---------------------------
                    # Build Documents
                    # ---------------------------
                    docs = []
                    for d in traveller.traveller_docs:
                        docs.append({
                            "documentType": d.document_type,
                            "birthPlace": d.birth_place,
                            "issuanceLocation": d.issuance_location,
                            "issuanceDate": d.issuance_date.strftime('%Y-%m-%d') if d.issuance_date else None,
                            "number": d.number,
                            "expiryDate": d.expiry_date.strftime('%Y-%m-%d') if d.expiry_date else None,
                            "issuanceCountry": d.issuance_country.code if d.issuance_country else None,
                            "validityCountry": d.validity_country.code if d.validity_country else None,
                            "nationality": d.nationality_country.code if d.nationality_country else None,
                            "holder": bool(d.holder),
                        })
                    traveller_dict = {
                        "id": str(travel_count),
                        "dateOfBirth": traveller.birth_date.strftime('%Y-%m-%d'),
                        "name": {
                            "firstName": traveller.firstname,
                            "lastName": traveller.lastname
                        },
                        "gender": traveller.gender,
                        "contact": {
                            "emailAddress": traveller.email,
                            "phones": phone_entry
                        },
                        "documents": docs
                    }
                    travellers_payload.append(traveller_dict)
                for cc in line.communication_ids:
                    phones_list = []
                    if cc.cc_phone:
                        phones_list.append({
                            "deviceType": "LANDLINE",
                            "countryCallingCode": str(cc.cc_country_id.phone_code) if cc.cc_country_id else "",
                            "number": cc.cc_phone,
                        })
                    if cc.cc_mobile:
                        phones_list.append({
                            "deviceType": "MOBILE",
                            "countryCallingCode": str(cc.cc_country_id.phone_code) if cc.cc_country_id else "",
                            "number": cc.cc_mobile,
                        })
                    address_data = {
                        "lines": list(filter(None, [cc.cc_street, cc.cc_street2])),
                        "postalCode": cc.cc_zip or "",
                        "cityName": cc.cc_city or "",
                        "countryCode": cc.cc_country_id.code if cc.cc_country_id else "",
                    }
                    contact_data = {
                        "addresseeName": {
                            "firstName": cc.cc_firstname or "",
                            "lastName": cc.cc_lastname or "",
                        },
                        "companyName": cc.cc_company_name or "",
                        "purpose": cc.cc_purpose,
                        "phones": phones_list,
                        "emailAddress": cc.cc_email or "",
                        "address": address_data,
                    }
                    contacts_payload.append(contact_data)
                body = {
                    "data": {
                        "type": "flight-order",
                        "flightOffers": json.loads(line.raw_pricing_json),
                        "travelers": travellers_payload,
                        "remarks": {
                            "general": [
                                {
                                    "subType": "GENERAL_MISCELLANEOUS",
                                    "text": "ONLINE BOOKING FROM INCREIBLE VIAJES"
                                }
                            ]
                        },
                        "ticketingAgreement": {
                            "option": "DELAY_TO_CANCEL",
                            "delay": "6D"
                        },
                        "contacts": contacts_payload,

                    }
                }
                return body
            else:
                return {}

        return {}