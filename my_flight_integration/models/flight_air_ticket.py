import requests
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
import json

class AirTicket(models.Model):
    _name = "air.ticket"
    _description = "Flight Air Ticket"

    name = fields.Char("Ticket No.", copy=False)
    reference = fields.Char("Reference")
    booking_date = fields.Datetime("Booking Date")
    flight_offer = fields.Char("Flight Offer ID")
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id.id,
    )
    base_price = fields.Monetary("Base Price", currency_field='currency_id')
    total_tax = fields.Monetary("Total tax" ,compute='_compute_total_tax', currency_field='currency_id', store=True)
    total_amount = fields.Monetary("Total", currency_field='currency_id')
    currency = fields.Char("Currency")
    provider_id = fields.Many2one('booking.conf.line', "Provider")
    flight_search_id = fields.Many2one('flight.search', "Flight Search")
    response_id = fields.Char("Id")
    office_id = fields.Char("Office ID")
    response_json = fields.Text("Full API Response")
    travel_info = fields.Text("Travel Information")
    travel_pricing_lines = fields.One2many('air.ticket.travel.pricing', 'air_ticket_id')
    travelers_ids = fields.One2many('air.ticket.travelers', 'air_ticket_id')

    @api.depends('travel_pricing_lines.total_tax')
    def _compute_total_tax(self):
        for rec in self:
            total_tax = 0
            if rec.travel_pricing_lines:
                line_tax = rec.travel_pricing_lines.mapped('total_tax')
                total_tax = sum(line_tax) if line_tax else 0.0
            rec.total_tax = total_tax

class AirTicketTravelPricing(models.Model):
    _name = "air.ticket.travel.pricing"
    _description = "Flight Air Ticket Travel pricing"

    air_ticket_id = fields.Many2one('air.ticket', string="Ticket id")
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id.id,
    )
    travel_id = fields.Integer("Id")
    fare_option = fields.Char("Fare Option")
    traveler_type = fields.Char("Traveler Type")
    associated_adult_id = fields.Char("Assosiated Adult")
    base_amount = fields.Monetary("Base amount", currency_field='currency_id')
    total_tax = fields.Monetary("Tax amount", currency_field='currency_id')
    total_amount = fields.Monetary("Total Amount", currency_field='currency_id')
    refundable_tax = fields.Monetary("Refundable Tax", currency_field='currency_id')
    segment_ids = fields.One2many('air.ticket.travel.pricing.segment', 'traveler_pricing_id')

class AirTicketTravelPricingSegment(models.Model):
    _name = "air.ticket.travel.pricing.segment"
    _description = "Flight Air Ticket Travel pricing segment"

    traveler_pricing_id = fields.Many2one('air.ticket.travel.pricing', string="Traveler Pricing Id")
    segment_id = fields.Char("Segment ID")
    cabin = fields.Char("Cabin")
    fare_basis = fields.Char("Fare Basis")
    t_class = fields.Char("Class")
    weight = fields.Char("Weight")
    weight_unit = fields.Char("Weight Unit")

class AirTicketTravelers(models.Model):
    _name = "air.ticket.travelers"
    _description = "Flight Air Ticket Travelers"

    air_ticket_id = fields.Many2one('air.ticket', string="Ticket id")
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
    doc_ids = fields.One2many(comodel_name='air.ticket.travelers.docs',
                              inverse_name='traveler_id',
                              string="Traveller Documents",
                              copy=True, auto_join=True)
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'air_traveller_docs_attachment_rel',
        'air_ticket_id',
        'attachment_id',
        string="Attachments"
    )

class AirTicketTravelersDocs(models.Model):
    _name = "air.ticket.travelers.docs"
    _description = "Flight Air Ticket Travelers Docs"

    traveler_id = fields.Many2one('air.ticket.travelers', string="Traveler id")
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

