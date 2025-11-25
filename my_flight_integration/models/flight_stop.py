from odoo import models, fields

class FlightStop(models.Model):
    _name = "flight.stop"
    _description = "Flight Stop Options"

    name = fields.Char()
    value = fields.Integer(string="Stops")
