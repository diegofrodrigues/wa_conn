from odoo import _, fields, models


class Message(models.Model):
    _name = 'mail.message'
    _inherit = 'mail.message'

    message_type = fields.Selection(
        selection_add=[('whatsapp', 'WhatsApp')],
        ondelete={'whatsapp': 'set default'}
    )
