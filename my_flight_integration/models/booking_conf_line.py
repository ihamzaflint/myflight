from odoo import models, fields, api


class BookingConfLine(models.Model):
    _name = "booking.conf.line"
    _description = "Booking Configuration Line"

    name = fields.Char(string="Name")
    url = fields.Char(string="URL")
    username = fields.Char(string="Username")
    password = fields.Char(string="Password")
    access_token = fields.Char(string="Access Token")
    company_id = fields.Many2one("res.company", string="Company")

    booking_conf_id = fields.Many2one('booking.conf')