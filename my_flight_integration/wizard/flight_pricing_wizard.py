from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json
import re
import requests
import logging
_logger = logging.getLogger(__name__)
from datetime import date, datetime

class FlightPricingWizard(models.TransientModel):
    _name = "flight.pricing.wizard"
    _description = "Flight Pricing Wizard"

    flight_search_line_id = fields.Many2one("flight.search.line", string="Flight Offer Line", readonly=True)
    base_price = fields.Char(string="Base Price", readonly=True)
    total_price = fields.Char(string="Total Price", readonly=True)
    currency = fields.Char(string="Currency", readonly=True)
    fare_type = fields.Char(string="Fare Type", readonly=True)
    validating_airline = fields.Char(string="Validating Airline", readonly=True)
    raw_pricing_json = fields.Text(string="Raw Pricing Data", readonly=True)
    refundable_taxes = fields.Char(string="Refundable Taxes", readonly=True)
    tax_summary = fields.Text(string="Tax Details", readonly=True)
    total_travels = fields.Integer(string="Total Travellers")
    total_adults = fields.Integer(string="Total Adults")
    total_childs = fields.Integer(string="Total Childs")
    total_held_infant = fields.Integer(string="Total Held Infant")
    total_seated_infant = fields.Integer(string="Total Seated Infant")
    travellers_ids = fields.One2many(comodel_name='pricing.traveller.line.wizard',
                                     inverse_name='pricing_id',
                                     string="Travelles",
                                     copy=True, auto_join=True)
    communication_ids = fields.One2many(comodel_name='contact.communication.line.wizard',
                                        inverse_name='pricing_id',
                                        string="Communications",
                                        copy=True, auto_join=True)

    def _format_duration(self, duration):
        """ Convert PT4H45M → 4 hours 45 minutes """
        hours = re.findall(r'(\d+)H', duration)
        minutes = re.findall(r'(\d+)M', duration)

        h = f"{hours[0]} hours" if hours else ""
        m = f"{minutes[0]} minutes" if minutes else ""

        return f"{h} {m}".strip()

    def _format_datetime(self, dt_string):
        """ Convert 2025-11-27T11:30:00 → 27 Nov 2025, 11:30 AM """
        if not dt_string:
            return ""
        dt = datetime.strptime(dt_string, "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%d %b %Y, %I:%M %p")

    def _format_iata(self, code):
        """ Fetch IATA details from DB """
        rec = self.env['iata.code'].search([('code', '=', code)], limit=1)
        if rec:
            return f"{rec.city}({rec.code})({rec.country})"
        return code


    def action_confirm(self):
        for rec in self:
            api_service = self.env['flight.api.service'].sudo()
            flight_search_id = rec.flight_search_line_id.flight_search_id
            flight_search_line_id = rec.flight_search_line_id
            config_line_id = rec.flight_search_line_id.conf_id
            if config_line_id.name == 'amadeus':
                if rec.total_travels and rec.travellers_ids:
                    line_for_adults = rec.travellers_ids.filtered(lambda t: t.traveller_type == 'ADULT')
                    line_for_childs = rec.travellers_ids.filtered(lambda t: t.traveller_type == 'CHILD')
                    line_for_seated = rec.travellers_ids.filtered(lambda t: t.traveller_type == 'SEATED_INFANT')
                    line_for_held = rec.travellers_ids.filtered(lambda t: t.traveller_type == 'HELD_INFANT')
                    if len(rec.travellers_ids) > rec.total_travels:
                        raise ValidationError("Traveller list are more than total travellers!!")
                    if len(rec.travellers_ids) < rec.total_travels:
                        raise ValidationError("Traveller list are less than total travellers!!")
                    if rec.total_childs > len(line_for_childs):
                        raise ValidationError(
                            "You can include only %s child in this flight ticket!!" % rec.total_childs)
                    if rec.total_childs < len(line_for_childs):
                        raise ValidationError(
                            "You should add total (%s) child in this flight ticket!!" % rec.total_childs)
                    if rec.total_adults > len(line_for_adults):
                        raise ValidationError(
                            "You can include only %s adult in this flight ticket!!" % rec.total_adults)
                    if rec.total_adults < len(line_for_adults):
                        raise ValidationError(
                            "You should add total (%s) adult in this flight ticket!!" % rec.total_adults)

                    if rec.total_seated_infant > len(line_for_seated):
                        raise ValidationError(
                            "You can include only %s seated infant in this flight ticket!!" % rec.total_seated_infant)
                    if rec.total_seated_infant < len(line_for_seated):
                        raise ValidationError(
                            "You should add total (%s) seated infant in this flight ticket!!" % rec.total_seated_infant)

                    if rec.total_held_infant > len(line_for_held):
                        raise ValidationError(
                            "You can include only %s held infant in this flight ticket!!" % rec.total_held_infant)
                    if rec.total_held_infant < len(line_for_held):
                        raise ValidationError(
                            "You should add total (%s) held infant in this flight ticket!!" % rec.total_held_infant)

                    end_point = '/booking/flight-orders'
                    body = api_service._prepare_body(flight_search_id, rec, service_provider=config_line_id.name,
                                                    end_point=end_point)
                    if body:
                        data = api_service.call_api(
                            api_type=config_line_id.name,
                            endpoint=end_point,
                            flight_search_id=flight_search_id.id,
                            payload=body,
                            version='v1'
                        )

                        # data = {"data": {"type": "flight-order", "id": "eJzTd9e3cHYNMw4EAAqdAkA", "queuingOfficeId": "NCE4D31SB", "associatedRecords": [{"reference": "8CEV3Q", "creationDate": "2025-11-24T11:03:00.000", "originSystemCode": "GDS", "flightOfferId": "3"}, {"reference": "8CEV3Q", "creationDate": "2025-11-24T11:03:00.000", "originSystemCode": "UL", "flightOfferId": "3"}], "flightOffers": [{"type": "flight-offer", "id": "3", "source": "GDS", "nonHomogeneous": False, "lastTicketingDate": "2025-11-28", "itineraries": [{"segments": [{"departure": {"iataCode": "BOM", "terminal": "2", "at": "2025-11-28T20:45:00"}, "arrival": {"iataCode": "CMB", "at": "2025-11-28T23:15:00"}, "carrierCode": "UL", "number": "144", "aircraft": {"code": "320"}, "duration": "PT2H30M", "id": "99", "numberOfStops": 0, "co2Emissions": [{"weight": 122, "weightUnit": "KG", "cabin": "ECONOMY"}]}, {"departure": {"iataCode": "CMB", "at": "2025-11-29T18:40:00"}, "arrival": {"iataCode": "DXB", "terminal": "1", "at": "2025-11-29T21:50:00"}, "carrierCode": "UL", "number": "225", "aircraft": {"code": "332"}, "duration": "PT4H40M", "id": "100", "numberOfStops": 0, "co2Emissions": [{"weight": 194, "weightUnit": "KG", "cabin": "ECONOMY"}]}]}], "price": {"currency": "USD", "total": "140.36", "base": "36.00", "fees": [{"amount": "0.00", "type": "TICKETING"}, {"amount": "0.00", "type": "SUPPLIER"}, {"amount": "0.00", "type": "FORM_OF_PAYMENT"}], "grandTotal": "140.36", "billingCurrency": "USD"}, "pricingOptions": {"fareType": ["PUBLISHED"], "includedCheckedBagsOnly": True}, "validatingAirlineCodes": ["UL"], "travelerPricings": [{"travelerId": "1", "fareOption": "STANDARD", "travelerType": "ADULT", "price": {"currency": "USD", "total": "140.36", "base": "36.00", "taxes": [{"amount": "8.20", "code": "IN"}, {"amount": "5.60", "code": "K3"}, {"amount": "14.16", "code": "P2"}, {"amount": "75.00", "code": "YQ"}, {"amount": "1.40", "code": "ZR"}], "refundableTaxes": "106.36"}, "fareDetailsBySegment": [{"segmentId": "99", "cabin": "ECONOMY", "fareBasis": "SOWIZ", "class": "S", "includedCheckedBags": {"weight": 30, "weightUnit": "KG"}}, {"segmentId": "100", "cabin": "ECONOMY", "fareBasis": "SOWIZ", "class": "S", "includedCheckedBags": {"weight": 30, "weightUnit": "KG"}}]}]}], "travelers": [{"id": "1", "dateOfBirth": "2007-11-24", "gender": "MALE", "name": {"firstName": "Rahul", "lastName": "Lalani"}, "documents": [{"number": "00000", "issuanceDate": "2024-09-17", "expiryDate": "2026-06-11", "issuanceCountry": "IN", "issuanceLocation": "JAMNAGAR", "birthPlace": "JAMNAGAR", "documentType": "VISA", "validityCountry": "IN"}], "contact": {"purpose": "STANDARD", "phones": [{"deviceType": "LANDLINE", "countryCallingCode": "91", "number": "159951159"}, {"deviceType": "MOBILE", "countryCallingCode": "91", "number": "9898992290"}], "emailAddress": "lalani@gmail.com"}}], "remarks": {"general": [{"subType": "GENERAL_MISCELLANEOUS", "text": "ONLINE BOOKING FROM INCREIBLE VIAJES"}]}, "ticketingAgreement": {"option": "DELAY_TO_CANCEL", "delay": "6D"}, "automatedProcess": [{"code": "IMMEDIATE", "queue": {"number": "0", "category": "0"}, "officeId": "NCE4D31SB"}], "contacts": [{"addresseeName": {"firstName": "Jethyo jado"}, "address": {"lines": ["AA", "BB"], "postalCode": "361001", "countryCode": "IN", "cityName": "JAMNAGAR"}, "purpose": "INVOICE", "companyName": "JETHULAL"}]}, "dictionaries": {"locations": {"BOM": {"cityCode": "BOM", "countryCode": "IN"}, "CMB": {"cityCode": "CMB", "countryCode": "LK"}, "DXB": {"cityCode": "DXB", "countryCode": "AE"}}}}
                        json_response = data.json()
                        # json_response = data

                        ticket_vals = {
                            'name': self.env['ir.sequence'].next_by_code('air.ticket'),
                            'flight_search_id': flight_search_id.id,
                            'provider_id': config_line_id.id,

                            'response_json': json.dumps(json_response),
                        }

                        try:
                            data_block = json_response.get('data')
                            if not data_block:
                                raise ValidationError("Invalid API Response: Missing data")

                            # -------------------------
                            # BASIC HEADER INFORMATION
                            # -------------------------
                            ticket_vals['response_id'] = data_block.get('id')
                            ticket_vals['office_id'] = data_block.get('queuingOfficeId')

                            # Associated records
                            associated_records = data_block.get('associatedRecords', [])
                            if associated_records:
                                ticket_vals['reference'] = associated_records[0].get('reference')
                                date_str = associated_records[0].get('creationDate')
                                if date_str:
                                    # Example: 2025-11-24T11:03:00.000
                                    ticket_vals['booking_date'] = datetime.strptime(
                                        date_str, "%Y-%m-%dT%H:%M:%S.%f"
                                    )

                            # -------------------------
                            # FLIGHT OFFER MAIN INFO
                            # -------------------------
                            flight_offers = data_block.get('flightOffers', [])
                            if flight_offers:
                                first_offer = flight_offers[0]
                                ticket_vals['flight_offer'] = first_offer.get('id')

                                price = first_offer.get('price', {})
                                if price:
                                    ticket_vals['base_price'] = price.get('base')
                                    ticket_vals['total_amount'] = float(price.get('grandTotal', 0))
                                    ticket_vals['currency'] = price.get('currency')

                            # -------------------------
                            # CREATE MAIN TICKET RECORD
                            # -------------------------
                            ticket_id = self.env['air.ticket'].sudo().create(ticket_vals)

                            # -------------------------
                            # EXTRACT TRAVEL INFO AND STORE IN FIELD
                            # -------------------------
                            travel_info_list = []
                            if flight_offers:
                                first_offer = flight_offers[0]
                                itineraries = first_offer.get('itineraries', [])

                                for iti_index, itinerary in enumerate(itineraries, start=1):
                                    travel_info_list.append(f"✈ Itinerary {iti_index}")

                                    for segm in itinerary.get('segments', []):
                                        dep = segm.get('departure', {})
                                        arr = segm.get('arrival', {})

                                        dep_airport = self._format_iata(dep.get('iataCode'))
                                        arr_airport = self._format_iata(arr.get('iataCode'))

                                        dep_time = self._format_datetime(dep.get('at', ""))
                                        arr_time = self._format_datetime(arr.get('at', ""))

                                        duration = self._format_duration(segm.get('duration', ""))

                                        carrier = segm.get('carrierCode')
                                        flight_no = segm.get('number')

                                        travel_info_list.append(
                                            f"""
                                Carrier: {carrier}-{flight_no}
                                From: {dep_airport}
                                Departure: {dep_time}
                                To: {arr_airport}
                                Arrival: {arr_time}
                                Duration: {duration}
                                """.strip()
                                        )
                            if travel_info_list:
                                ticket_id.travel_info = "\n\n".join(travel_info_list)
                            # ===========================================================
                            # TRAVELER PRICING LINES
                            # ===========================================================
                            traveler_pricings = first_offer.get('travelerPricings', [])
                            for pricing in traveler_pricings:

                                price = pricing.get('price', {})
                                total_tax = sum(
                                    float(t.get('amount', 0)) for t in price.get('taxes', [])
                                )

                                pricing_record = self.env['air.ticket.travel.pricing'].sudo().create({
                                    'air_ticket_id': ticket_id.id,
                                    'travel_id': pricing.get('travelerId'),
                                    'fare_option': pricing.get('fareOption'),
                                    'traveler_type': pricing.get('travelerType'),
                                    'associated_adult_id': pricing.get('associatedAdultId'),
                                    'base_amount': float(price.get('base', 0)),
                                    'total_amount': float(price.get('total', 0)),
                                    'refundable_tax': float(price.get('refundableTaxes', 0)),
                                    'total_tax': total_tax,
                                })

                                # SEGMENTS
                                for seg in pricing.get('fareDetailsBySegment', []):
                                    self.env['air.ticket.travel.pricing.segment'].sudo().create({
                                        'traveler_pricing_id': pricing_record.id,
                                        'segment_id': seg.get('segmentId'),
                                        'cabin': seg.get('cabin'),
                                        'fare_basis': seg.get('fareBasis'),
                                        't_class': seg.get('class'),
                                        'weight': str(seg.get('includedCheckedBags', {}).get('weight')),
                                        'weight_unit': seg.get('includedCheckedBags', {}).get('weightUnit'),
                                    })

                            # ===========================================================
                            # TRAVELER DETAILS
                            # ===========================================================
                            for tr in data_block.get('travelers', []):
                                traveller = rec.travellers_ids.filtered(lambda l: l.firstname == tr.get('name', {}).get('firstName')
                                                                                  and l.lastname == tr.get('name', {}).get('lastName')
                                                                                  and l.birth_date.strftime('%Y-%m-%d') == tr.get('dateOfBirth'))

                                attachment_commands = []
                                if traveller:
                                    if traveller[0].traveller_docs:
                                        all_attachment_ids = []
                                        for doc in traveller.traveller_docs:
                                            if doc.attachment_ids:  # safety check
                                                all_attachment_ids.extend(doc.attachment_ids.ids)

                                        if all_attachment_ids:
                                            attachment_commands = [(6, 0, all_attachment_ids)]

                                traveler_record = self.env['air.ticket.travelers'].sudo().create({
                                    'air_ticket_id': ticket_id.id,
                                    'firstname': tr.get('name', {}).get('firstName'),
                                    'lastname': tr.get('name', {}).get('lastName'),
                                    'gender': tr.get('gender'),
                                    'birth_date': tr.get('dateOfBirth'),
                                    'attachment_ids': attachment_commands
                                })

                                # CONTACT
                                contact = tr.get('contact', {})
                                traveler_record.email = contact.get('emailAddress')

                                phones = contact.get('phones', [])
                                mobile = next((p for p in phones if p.get('deviceType') == 'MOBILE'), None)
                                landline = next((p for p in phones if p.get('deviceType') == 'LANDLINE'), None)

                                if mobile:
                                    traveler_record.mobile = mobile.get('number')
                                if landline:
                                    traveler_record.phone = landline.get('number')

                                # DOCUMENTS
                                for d in tr.get('documents', []):
                                    vals = {
                                        'traveler_id': traveler_record.id,
                                        'document_type': d.get('documentType'),
                                        'birth_place': d.get('birthPlace'),
                                        'issuance_location': d.get('issuanceLocation'),
                                        'number': d.get('number')
                                    }

                                    if d.get('issuanceDate'):
                                        vals['issuance_date'] = datetime.strptime(
                                            d['issuanceDate'], "%Y-%m-%d"
                                        ).date()
                                    if d.get('expiryDate'):
                                        vals['expiry_date'] = datetime.strptime(
                                            d['expiryDate'], "%Y-%m-%d"
                                        ).date()

                                    for field_name, country_code in [
                                        ('issuance_country', d.get('issuanceCountry')),
                                        ('validity_country', d.get('validityCountry')),
                                        ('nationality_country', d.get('nationality')),
                                    ]:
                                        if country_code:
                                            vals[field_name] = self.env['res.country'].search(
                                                [('code', '=', country_code)], limit=1
                                            ).id

                                    self.env['air.ticket.travelers.docs'].sudo().create(vals)

                        except Exception as e:
                            raise ValidationError(f"Ticket creation failed: {str(e)}")

                        # -----------------------------------------------------------
                        # RETURN: OPEN THE NEWLY CREATED TICKET FORM VIEW
                        # -----------------------------------------------------------
                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'air.ticket',
                            'view_mode': 'form',
                            'res_id': ticket_id.id,
                            'target': 'current',
                        }
                    else:
                        raise ValidationError("Request body not found!!")

                else:
                    raise ValidationError("Traveller not found for this flight!!")
            else:
                pass
        else:
            pass

class ContactCommunicationLineWizard(models.TransientModel):
    _name = "contact.communication.line.wizard"
    _description = "Communications Contacts will be saved here"

    pricing_id = fields.Many2one(comodel_name='flight.pricing.wizard',
                                 string="Pricing",
                                 required=True, ondelete='cascade', index=True, copy=False)

    cc_firstname = fields.Char("Firstname")
    cc_lastname = fields.Char("Lastname")
    cc_company_name = fields.Char("Company Name")
    cc_purpose = fields.Selection([
        ('STANDARD', 'STANDARD'),
        ('INVOICE', 'INVOICE'),
        ('STANDARD_WITHOUT_TRANSMISSION', 'STANDARD_WITHOUT_TRANSMISSION'),
    ], string="Purpose", default='STANDARD', required=True)
    cc_email = fields.Char("Email")
    cc_phone = fields.Char("Landline")
    cc_mobile = fields.Char("Mobile")
    cc_street = fields.Char()
    cc_street2 = fields.Char()
    cc_zip = fields.Char()
    cc_city = fields.Char()
    cc_country_id = fields.Many2one('res.country', string="Country")
    cc_state_id = fields.Many2one(
        'res.country.state',
        string="State", domain="[('country_id', '=?', cc_country_id)]"
    )

    @api.onchange('cc_email')
    def _onchange_cc_email(self):
        if self.cc_email:
            email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_regex, self.cc_email):
                raise ValidationError("Please enter a valid email address.")

    @api.onchange('cc_mobile', 'cc_phone')
    def _onchange_mobile(self):
        if self.cc_phone and not re.match(r'^[0-9\+\-\(\) ]+$', self.cc_phone):
            raise ValidationError("Please enter a valid phone number for communication person.")
        if self.cc_mobile and not re.match(r'^[0-9\+\-\(\) ]+$', self.cc_mobile):
            raise ValidationError("Please enter a valid mobile number communication person.")



class PricingTravellerLineWizard(models.TransientModel):
    _name = "pricing.traveller.line.wizard"
    _description = "Pricing Traveller Line Wizard"

    pricing_id = fields.Many2one(comodel_name='flight.pricing.wizard',
                                   string="Pricing",
                                   required=True, ondelete='cascade', index=True, copy=False)
    firstname = fields.Char("Firstname")
    lastname = fields.Char("Lastname")
    gender = fields.Selection([
        ('MALE', 'MALE'),
        ('FEMALE', 'FEMALE'),
        ('UNSPECIFIED', 'UNSPECIFIED'),
        ('UNDISCLOSED', 'UNDISCLOSED'),
    ], string="Gender", default='MALE', required=True)
    birth_date = fields.Date(string="Birth Date", required=True)
    traveller_type = fields.Selection([
        ('ADULT', 'ADULT'),
        ('CHILD', 'CHILD'),
        ('SEATED_INFANT', 'SEATED INFANT'),
        ('HELD_INFANT', 'HELD INFANT'),
    ], string="TYPE")
    email = fields.Char("Email")
    phone = fields.Char("Phone")
    mobile = fields.Char("Mobile")
    traveller_country_id = fields.Many2one('res.country', string="Country")
    traveller_docs = fields.One2many(comodel_name='traveller.wizard.docs',
                              inverse_name='pricing_line_id',
                              string="Traveller Documents",
                              copy=True, auto_join=True)

    emg_address = fields.Text("Address")
    emg_country_id = fields.Many2one("res.country", string="Country")
    emg_country_code = fields.Char("Country Code")
    emg_number = fields.Char("Mobile Number")
    emg_text = fields.Text("Additional Text")

    @api.onchange('emg_country_id')
    def _onchange_emg_country_code(self):
        for rec in self:
            if rec.emg_country_id:
                rec.emg_country_code = rec.emg_country_id.code if rec.emg_country_id else ''

    @api.onchange('email')
    def _onchange_email(self):
        if self.email:
            email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_regex, self.email):
                raise ValidationError("Please enter a valid email address.")

    @api.onchange('mobile', 'emg_number', 'phone')
    def _onchange_mobile(self):
        if self.phone and not re.match(r'^[0-9\+\-\(\) ]+$', self.phone):
            raise ValidationError("Please enter a valid phone number.")
        if self.mobile and not re.match(r'^[0-9\+\-\(\) ]+$', self.mobile):
            raise ValidationError("Please enter a valid mobile number.")
        if self.emg_number and not re.match(r'^[0-9\+\-\(\) ]+$', self.emg_number):
            raise ValidationError("Please enter a valid emergency mobile number.")

    @api.onchange('birth_date')
    def check_traveller_type(self):
        for rec in self:
            if rec.birth_date:
                today = date.today()
                age = today.year - rec.birth_date.year - (
                        (today.month, today.day) < (rec.birth_date.month, rec.birth_date.day)
                )
                if age > 2 and age < 12:
                    rec.traveller_type = 'CHILD'
                elif age > 11:
                    rec.traveller_type = 'ADULT'
            else:
                rec.traveller_type = False

    class TravellerWizardDocs(models.TransientModel):
        _name = "traveller.wizard.docs"

        pricing_line_id = fields.Many2one(comodel_name='pricing.traveller.line.wizard',
                                     string="Pricing",
                                    ondelete='cascade', index=True, copy=False)
        document_type = fields.Selection([
            ('VISA', 'VISA'),
            ('PASSPORT', 'PASSPORT'),
            ('IDENTITY_CARD', 'IDENTITY_CARD'),
            ('KNOWN_TRAVELER', 'KNOWN_TRAVELER'),
            ('REDRESS', 'REDRESS'),
        ], string="Document Type", default='VISA')
        birth_place = fields.Char("BirthPlace")
        issuance_location = fields.Char("Issue Location")
        issuance_date = fields.Date("Issue Date")
        number = fields.Char("Number")
        expiry_date = fields.Date(string="Expiry Date")
        issuance_country = fields.Many2one('res.country', string="Issue Country")
        validity_country = fields.Many2one('res.country', string="Validity Country")
        nationality_country = fields.Many2one('res.country', string="Nationality Country")
        holder = fields.Boolean(string="Holder")
        attachment_ids = fields.Many2many(
            'ir.attachment',
            'traveller_docs_attachment_rel',
            'wizard_doc_id',
            'attachment_id',
            string="Attachments"
        )