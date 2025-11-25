from odoo import models, fields, api


class BookingConf(models.Model):
    _name = "booking.conf"
    _description = "Booking Configuration"

    name = fields.Char(string="Name")

    line_ids = fields.One2many('booking.conf.line', 'booking_conf_id')