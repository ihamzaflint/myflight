from odoo import models, fields, api


class FlightApiLog(models.Model):
    _name = "flight.api.log"
    _description = "Store each api log request and response"

    name = fields.Char(string="Name")
    log_type = fields.Selection([
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error')
    ], string="Log type")
    type = fields.Selection([
        ('request', 'Request'),
        ('response', 'Response'),
        ('error', 'Error')
    ], string="Type")
    url = fields.Char("Url")
    code = fields.Char("Code")
    status = fields.Char("Status")
    title = fields.Char("Title")
    detail = fields.Char("Detail")
    reference = fields.Char("Reference")
    provider_id = fields.Many2one('booking.conf.line', string="Provider")
    flight_search_id = fields.Many2one('flight.search', string="Flight Search")
    flight_search_line_id = fields.Many2one('flight.search.line', string="Flight Search Line")
    request_payload = fields.Text(string="Payload")
    response_payload = fields.Text(string="Response")
    request_date = fields.Datetime('Date')
