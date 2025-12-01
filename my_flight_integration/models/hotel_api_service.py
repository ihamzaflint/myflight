import requests
from odoo import models, api, _
from odoo.exceptions import UserError
import json
from datetime import datetime


class HotelApiService(models.AbstractModel):
    _name = 'hotel.api.service'
    _description = 'Global Hotel API Service'


    @api.model
    def _get_hotel_api_config(self, provider_name):
        """
        Get hotel API config for a specific provider.
        Example provider_name: 'GENX', 'TBO', 'HOTELBEDS'
        """
        hotel_conf = self.env.ref('my_flight_integration.booking_conf_hotel')
        config = self.env['booking.conf.line'].search([
            ('booking_conf_id', '=', hotel_conf.id),
            ('code', '=', provider_name),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not config:
            raise UserError(_(
                "Hotel API configuration not found for provider: %s"
            ) % provider_name)

        return {
            "base_url": config.url.rstrip("/"),
            "username": config.username,
            "password": config.password,
            "access_token": config.access_token,
            "provider": provider_name,
        }


    def _get_header(self, provider):
        header = {}
        if provider in ['GenX']:
            header['Content-Type'] = 'application/json'
            header['Accept'] = 'application/json'

        return header


    def _get_default_payload(self, provider, endpoint, **kwargs):
        """
        Returns a payload template based on the API endpoint.
        kwargs allow overriding fields dynamically.
        """
        payload_map = {}
        if provider in ['GenX']:
            payload_map = {
                "/hotelcodelist" : {
                    "CountryCode" : kwargs.get("CountryCode")
                },

                "/Search": {
                    "CheckIn": kwargs.get("CheckIn"),
                    "CheckOut": kwargs.get("CheckOut"),
                    "HotelCodes": kwargs.get("HotelCodes", ""),
                    "CityCode": kwargs.get("CityCode", ""),
                    "GuestNationality": kwargs.get("GuestNationality", "AE"),
                    "PreferredCurrencyCode": kwargs.get("currency", "AED"),
                    "PaxRooms": kwargs.get("PaxRooms", []),
                    "IsDetailResponse": True,
                    "ResponseTime": kwargs.get("response_time", 23),
                    "Filters": kwargs.get("Filters", {
                        "MealType": "All",
                        "Refundable": "false",
                        "NoOfRooms": 2000000
                    })
                },

                "/HotelRoom": {
                    "BookingCode": kwargs.get("BookingCode")
                },

                "/Prebook": {
                    "BookingCode": kwargs.get("BookingCode"),
                    "PaymentMode": kwargs.get("PaymentMode", "Limit")
                },

                "/HotelBook": {
                    "BookingCode": kwargs.get("BookingCode"),
                    "CustomerDetails": kwargs.get("CustomerDetails", []),
                    "BookingType": kwargs.get("BookingType", "Voucher"),
                    "ClientReferenceId": kwargs.get("ClientReferenceId"),
                    "BookingReferenceId": kwargs.get("BookingReferenceId"),
                    "PaymentMode": kwargs.get("PaymentMode", "Limit"),
                    "GuestNationality": kwargs.get("GuestNationality"),
                    "TotalFare": kwargs.get("TotalFare"),
                    "EmailId": kwargs.get("EmailId"),
                    "PhoneNumber": kwargs.get("PhoneNumber")
                },

                "/BookingDetail": {
                    "BookingReferenceId": kwargs.get("BookingReferenceId"),
                    "PaymentMode": kwargs.get("PaymentMode", "Limit"),
                },

                "/Cancel": {
                    "ConfirmationNumber": kwargs.get("ConfirmationNumber")
                },

                "/Hoteldetails": {
                    "Hotelcodes": kwargs.get("Hotelcodes"),
                    "Language": kwargs.get("lang", "en")
                },

                "/BookingDetailsBasedOnDate": {
                    "FromDate": kwargs.get("FromDate"),
                    "ToDate": kwargs.get("ToDate")
                },

                "/CityList": {
                    "CountryCode": kwargs.get("CountryCode")
                },
            }
        return payload_map.get(endpoint, {})


    def _hotel_api_call(self, provider, endpoint, method="POST", payload=None, params=None):
        cfg = self._get_hotel_api_config(provider)
        header = self._get_header(provider)

        url = f"{cfg['base_url']}{endpoint}"
        start_time = datetime.now()

        try:
            response = requests.request(
                method=method,
                url=url,
                json=payload,
                params=params,
                headers=header,
                auth=(cfg["username"], cfg["password"]) if cfg["username"] else None,
            )

            duration = (datetime.now() - start_time).total_seconds() * 1000  # ms

            # Call log function (no duplication)
            self._create_api_log(
                provider=provider,
                endpoint=endpoint,
                method=method,
                payload=payload,
                response_payload=self._safe_json(response),
                status_code=response.status_code,
                duration_ms=duration,
                is_success=response.status_code in (200, 201),
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000

            # Log exception
            self._create_api_log(
                provider=provider,
                endpoint=endpoint,
                method=method,
                payload=payload,
                response_payload="",
                status_code=0,
                duration_ms=duration,
                is_success=False,
                error_message=str(e),
            )

            raise

        # Parse JSON response
        try:
            return response.json()
        except:
            raise UserError(_("Invalid JSON received from Hotel API for endpoint %s") % endpoint)


    def _create_api_log(
        self,
        provider,
        endpoint,
        method,
        payload,
        response_payload,
        status_code,
        duration_ms,
        is_success,
        error_message=None
    ):
        """Reusable method to create Hotel API logs."""

        self.env["hotel.api.log"].create({
            "provider": provider,
            "endpoint": endpoint,
            "method": method,
            "request_payload": json.dumps(payload, indent=4) if payload else "",
            "response_payload": response_payload or "",
            "status_code": status_code,
            "duration_ms": duration_ms,
            "is_success": is_success,
            "error_message": error_message,
            "company_id": self.env.company.id,
            "user_id": self.env.user.id,
        })


    def _safe_json(self, response):
        try:
            return json.dumps(response.json(), indent=4)
        except:
            return response.text or ""


    def call_hotel_api(self, provider, action, **kwargs):
        """
        Unified hotel API dispatcher.
        Automatically maps API names to endpoints + builds payload.
        """
        API_ENDPOINTS = {
            "search": "/Search",
            "hotel_room": "/HotelRoom",
            "prebook": "/Prebook",
            "book": "/HotelBook",
            "booking_detail": "/BookingDetail",
            "hotel_details": "/Hoteldetails",
            "hotel_code_list": "/hotelcodelist",
            "city_list": "/CityList",
            "country_list": "/CountryList",
        }

        if action not in API_ENDPOINTS:
            raise UserError(f"Invalid API action: {action}")

        endpoint = API_ENDPOINTS[action]

        # Build payload automatically if not provided
        payload = self._get_default_payload(provider, endpoint, **kwargs)
        if payload == {}:
            raise UserError(f"Payload could not be generated for action '{action}'. "
                            f"Check your passed parameters: {kwargs}")

        return self._hotel_api_call(provider, endpoint, payload=payload)
