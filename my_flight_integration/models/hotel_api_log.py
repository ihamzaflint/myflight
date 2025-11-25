from odoo import models, fields, api
import json


class HotelApiLog(models.Model):
    _name = "hotel.api.log"
    _description = "Hotel API Logs"
    _order = "create_date desc"

    provider = fields.Char(string="Provider")
    endpoint = fields.Char(string="Endpoint")
    method = fields.Char(string="Method", default="POST")

    request_payload = fields.Text(string="Request Payload")
    response_payload = fields.Text(string="Response Payload")
    status_code = fields.Integer(string="Status Code")

    is_success = fields.Boolean(string="Success", default=False)
    duration_ms = fields.Float(string="Duration (ms)")

    user_id = fields.Many2one("res.users", string="Requested By", default=lambda self: self.env.user)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)

    error_message = fields.Text(string="Error Message")

    # Pretty JSON for tree/form views
    def prettify_json(self, data):
        try:
            return json.dumps(data, indent=4, ensure_ascii=False)
        except:
            return data