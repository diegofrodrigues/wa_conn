from odoo import fields, models

class WaChannelStage(models.Model):
    _name = 'wa.channel.stage'
    _description = 'WhatsApp Channel Stage'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(string='Folded by default')
