from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HotelCancelWizard(models.TransientModel):
    _name = "hotel.cancel.wizard"
    _description = "Cancel Hotel Booking Wizard"
    _inherit = ["hotel.api.service"]

    booking_detail_id = fields.Many2one("hotel.booking.detail", required=True)
    confirmation_number = fields.Char(readonly=True)
    text = fields.Text()


    def action_confirm_cancel(self):
        """Call Cancel API and update booking status"""

        provider = "GenX"

        if not self.confirmation_number:
            raise ValidationError("Confirmation number missing!")

        payload = {
            "ConfirmationNumber": self.confirmation_number
        }

        # ===== CALL CANCEL API =====
        response = self.call_hotel_api(
            provider,
            "cancel",
            **payload
        )

        if not response:
            raise ValidationError("Cancel API returned no response!")

        status = response.get("Status", {})
        code = status.get("Code")

        if code != "200":
            raise ValidationError(f"Cancellation failed! API Response: {status.get('Description')}")

        # ===== Update booking status =====
        self.booking_detail_id.write({
            "state": "cancelled",
        })

        self.booking_detail_id.hotel_search_id.write({
            "state": "cancelled",
        })
