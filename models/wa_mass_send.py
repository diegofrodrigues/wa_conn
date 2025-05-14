import time
import random
from odoo import api, fields, models, _

class WAMassSend(models.TransientModel):
    _name = 'wa.mass.send'
    _description = 'Mass WhatsApp Sender'

    whatsapp_account_id = fields.Many2one(
        'wa.account',
        string="WhatsApp Account",
        required=True,
        help="WhatsApp account to use."
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        required=True,
        help="Recipients to send WhatsApp messages to."
    )
    template_id = fields.Many2one(
        'wa.template',
        string="Template",
        help="WhatsApp template to use."
    )
    message = fields.Html(string="Message", required=True, help="Message to send.")
    min_delay = fields.Integer(string="Min Delay (seconds)", default=2, required=True)
    max_delay = fields.Integer(string="Max Delay (seconds)", default=10, required=True)

    def send_mass_message(self):
        """
        Send WhatsApp messages to all selected partners with a random delay between each send.
        """
        mixin = self.env['wa.mixin']
        for partner in self.partner_ids:
            if not partner.mobile:
                continue
            mixin.send_whatsapp(
                mobile=partner.mobile,
                message=self.message,
                media=self.template_id.whatsapp_media if self.template_id else False,
                media_filename=self.template_id.whatsapp_media_filename if self.template_id else False,
                whatsapp_account_id=self.whatsapp_account_id.id
            )
            delay = random.uniform(self.min_delay, self.max_delay)
            time.sleep(delay)
