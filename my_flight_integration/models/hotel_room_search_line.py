from odoo import models, fields, api
import json
from datetime import datetime


class HotelRoomSearchLine(models.Model):
    _name = "hotel.room.search.line"
    _description = "Hotel Search Line"
    _inherit = ["hotel.api.service"]

    name = fields.Html(string="Name")
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id.id,
    )
    price = fields.Monetary(currency_field='currency_id')
    raw_json_data = fields.Text()
    conf_id = fields.Many2one('booking.conf.line')

    hotel_booking_id = fields.Many2one('hotel.room.search')
    booking_code = fields.Char()
    meal_type = fields.Char()


    def action_select_room(self):
        self.ensure_one()

        return {
            "name": "Hotel Room Details",
            "type": "ir.actions.act_window",
            "res_model": "hotel.room.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_id": self.id,
            }
        }