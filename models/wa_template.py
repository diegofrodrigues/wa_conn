from odoo import _, api, fields, models
from odoo.tools import html2plaintext


class WATemplate(models.Model):
    _name = 'wa.template'
    _description = 'WhatsApp Template'

    name = fields.Char(string="Template Name", required=True, help="Name of the WhatsApp template.")
    model = fields.Char('Related Document Model', related='model_id.model', index=True, store=True, readonly=True)
    model_id = fields.Many2one(
        'ir.model', string="Applies to", required=True, ondelete='cascade',
        help="The model this template applies to (e.g., Sale Order, Invoice)."
    )
    message = fields.Text(string="Message", required=True, translate=True)
    whatsapp_media = fields.Binary(string="Media File", help="Attach a media file for the template.")
    whatsapp_media_filename = fields.Char(string="Media Filename", help="Filename of the media file.")
    attachment_ids = fields.Many2many(
        'ir.attachment', 'whatsapp_template_ir_attachments_rel',
        'template_id', 'attachment_id', string="Attachments",
        help="Attachments to include with the WhatsApp message."
    )

    def render_template(self, template_field, record):
        """
        Render the template field for the given record.
        :param template_field: The field to render (e.g., 'message').
        :param record: The record to use for rendering.
        :return: Rendered content.
        """
        self.ensure_one()
        if not record:
            return ''
        template = self[template_field]
        if not template:
            return ''
        return self.env['mail.render.mixin']._render_field(template, record.ids, self.model_id.model)[record.id]

    def generate_whatsapp_values(self, record):
        """
        Generate WhatsApp message values for the given record.
        :param record: The record to use for generating values.
        :return: A dictionary of WhatsApp message values.
        """
        self.ensure_one()
        message = self.render_template('message', record)
        message_plaintext = html2plaintext(message)
        return {
            'message': message_plaintext,
            'whatsapp_media': self.whatsapp_media,
            'whatsapp_media_filename': self.whatsapp_media_filename,
            'attachment_ids': self.attachment_ids.ids,
        }
