from odoo import models, fields, api
import json
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

class FlightSearchLine(models.Model):
    _name = "flight.search.line"
    _description = "Flight Search Line"

    name = fields.Char(string="Name")
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id.id,
    )
    price = fields.Monetary(currency_field='currency_id')
    location = fields.Char()
    duration = fields.Char()
    raw_json_data = fields.Text()
    stops = fields.Integer(string="Stops")
    flight_search_id = fields.Many2one('flight.search', string="Flight Search")
    conf_id = fields.Many2one('booking.conf.line')

    def action_search_flight_price(self):
        api_service = self.env['flight.api.service'].sudo()
        wizard = False
        wizard_data = {}
        for rec in self:
            if rec.conf_id and rec.raw_json_data:
                conf_line = rec.conf_id
                end_point = ''
                if conf_line.code == 'amadeus':
                    end_point = '/shopping/flight-offers/pricing'
                body = api_service._prepare_body(rec.flight_search_id, rec, service_provider=conf_line.code, end_point=end_point)
                data = api_service.call_api(
                    api_type=conf_line.code,
                    endpoint=end_point,
                    flight_search_id=rec.flight_search_id.id,
                    payload=body,
                    version='v1'
                )
                data = data.json()
                priced_offer = data.get("data", {}).get("flightOffers", [{}])[0]
                price = priced_offer.get("price", {})
                traveler_pricing = priced_offer.get("travelerPricings", [])
                tax_texts = []
                refundable_taxes = False
                total_travels = 0
                total_adults = 0
                total_childs = 0
                total_held_infant = 0
                total_seated_infant = 0
                for traveler in traveler_pricing:
                    total_travels += 1
                    travelerType = traveler.get('travelerType')
                    if travelerType == 'ADULT':
                        total_adults += 1
                    if travelerType == 'CHILD':
                        total_childs += 1
                    if travelerType == 'HELD_INFANT':
                        total_held_infant += 1
                    if travelerType == 'SEATED_INFANT':
                        total_seated_infant += 1
                    taxes = traveler.get("price", {}).get("taxes", [])
                    refundable_taxes = traveler.get("price").get("refundableTaxes", "0.0")
                    if taxes:
                        t_str = ", ".join(
                            f"{tax.get('code', '')} — {tax.get('amount', '')} {traveler.get('price', {}).get('currency', '')}"
                            for tax in taxes
                        )
                        tax_texts.append(f"Traveler {traveler.get('travelerId', '')}: {t_str}")
                traveller_lines = []
                today = date.today()
                # for i in range(1, total_travels + 1):
                #     traveller_lines.append((0, 0, {
                #         'firstname': f"Traveller {i}",
                #     }))
                for i in range(1, total_adults + 1):
                    birthdate = today - relativedelta(years=18)  # 18 years old minimum
                    traveller_lines.append((0, 0, {
                        'firstname': f"Adult Traveller {i}",
                        'birth_date': birthdate,
                        'traveller_type': 'ADULT',
                    }))

                # --- CHILD TRAVELLERS ---
                for i in range(1, total_childs + 1):
                    # Example making them 10 years old (you can randomize if needed)
                    birthdate = today - relativedelta(years=11)
                    traveller_lines.append((0, 0, {
                        'firstname': f"Child Traveller {i}",
                        'birth_date': birthdate,
                        'traveller_type': 'CHILD',
                    }))

                for i in range(1, total_seated_infant + 1):
                    # Example making them 10 years old (you can randomize if needed)
                    birthdate = today - relativedelta(years=1)
                    traveller_lines.append((0, 0, {
                        'firstname': f"SeatedInfant Traveller {i}",
                        'birth_date': birthdate,
                        'traveller_type': 'SEATED_INFANT',
                    }))

                for i in range(1, total_held_infant + 1):
                    # Example making them 10 years old (you can randomize if needed)
                    birthdate = today - relativedelta(years=1)
                    traveller_lines.append((0, 0, {
                        'firstname': f"HeldInfant Traveller {i}",
                        'birth_date': birthdate,
                        'traveller_type': 'HELD_INFANT',
                    }))
                wizard_data.update({
                            'base_price': float(price.get('base', '0.0')),
                            'total_price': float(price.get('grandTotal', '0.0')),
                            'currency': price.get('currency', '-'),
                            'currency_id': rec.currency_id.id,
                            'fare_type': ", ".join(priced_offer.get("pricingOptions", {}).get("fareType", [])),
                            'validating_airline': ", ".join(priced_offer.get("validatingAirlineCodes", [])),
                            'refundable_taxes': float(refundable_taxes),
                            'tax_summary': "\n".join(tax_texts) or "No tax details found.",
                            'raw_pricing_json': json.dumps(data.get("data", {}).get("flightOffers", [{}])),
                            'total_travels': total_travels,
                            'total_adults': total_adults,
                            'total_childs': total_childs,
                            'total_held_infant': total_held_infant,
                            'total_seated_infant': total_seated_infant,
                            'travellers_ids': traveller_lines,
                            'flight_search_line_id': rec.id
                        })
                wizard = self.env['flight.pricing.wizard'].create(wizard_data)
        return {
            "type": "ir.actions.act_window",
            "name": "Flight Price Details",
            "res_model": "flight.pricing.wizard",
            "view_mode": "form",
            "target": "new",
            "res_id": wizard.id,
        }