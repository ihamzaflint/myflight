from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    service_requested = fields.Selection([
        ('flight', 'Flight Ticket'),
        ('hotel', 'Hotel Booking'),
        ('car', 'Car Rental')],
        string='Service', copy=False,
        default='flight')

    flight_ticket_type = fields.Selection([
        ('oneway', 'One Way'),
        ('twoway', 'Two Way')],
        string = 'Ticket Type', copy = False,
        default = 'oneway')

    departure_date = fields.Date(string="Departure")
    return_date = fields.Date(string="Return")
    check_in = fields.Date(string="Check-in From")
    check_out = fields.Date(string="Check-out To")

    @api.onchange('check_in', 'check_out')
    def _onchange_check_in_out(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                if rec.check_in > rec.check_out:
                    raise ValidationError(_('Check-in date cannot be greater than Check-out date.'))

    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for rec in self:
            if rec.check_in and rec.check_out and rec.check_in > rec.check_out:
                raise ValidationError(_('Check-in date cannot be greater than Check-out date.'))

    @api.onchange('departure_date', 'return_date')
    def _onchange_departure_return(self):
        for rec in self:
            if rec.departure_date and rec.return_date:
                if rec.departure_date > rec.return_date:
                    raise ValidationError(_('Departure date cannot be greater than Return date.'))

    @api.constrains('departure_date', 'return_date')
    def _check_departure_return(self):
        for rec in self:
            if rec.departure_date and rec.return_date and rec.departure_date > rec.return_date:
                raise ValidationError(_('Departure date cannot be greater than Return date.'))

