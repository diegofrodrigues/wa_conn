from odoo import _, api, fields, models


class WhatsAppTemplate(models.Model):
    _name = 'whatsapp.template'
    _description = 'WhatsApp Message Template'

    name = fields.Char(string="Template Name", required=True, help="Name of the WhatsApp template.")
    message = fields.Text(string="Message", required=True, help="The message content of the template.")
    whatsapp_media = fields.Binary(string="Media File", help="Attach a media file for the template.")
    whatsapp_media_filename = fields.Char(string="Media Filename", help="Filename of the media file.")
