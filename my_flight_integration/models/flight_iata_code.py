from odoo import fields, models

class IATACode(models.Model):
    _name = "iata.code"
    _description = "IATA Code"
    _rec_name = "city"

    city = fields.Char(string="City/Airport")
    country = fields.Char(string="Country")
    code = fields.Char(string="IATA Code")