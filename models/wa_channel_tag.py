from odoo import fields, models


class WaChannelTag(models.Model):
    _name = 'wa.channel.tag'
    _description = 'WhatsApp Channel Tag'
    _order = 'name'

    name = fields.Char(required=True, translate=False)
    color = fields.Integer(string='Color Index', default=1)
