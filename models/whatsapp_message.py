from odoo import _, api, fields, models


class WhatsappMessage(models.Model):
    _name = 'whatsapp.message'
    _description = 'WhatsApp Message'

    message = fields.Text(string="WhatsApp Message", help="Message to send via WhatsApp.")
    whatsapp_media = fields.Binary(string="WhatsApp Media", help="Media to send via WhatsApp.")
    whatsapp_media_filename = fields.Char(string="WhatsApp Media Filename", help="Filename of the media to send via WhatsApp.")
    whatsapp_media_mimetype = fields.Char(string="WhatsApp Media Mimetype", help="Mimetype of the media to send via WhatsApp.")
    message_id = fields.Many2one(
        'mail.message',
        string="Mail Message",
        help="Related mail message for this WhatsApp message."
    )  # Updated field name
