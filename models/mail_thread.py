from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def message_post(self, wa_message_id=None, **kwargs):
        if wa_message_id:
            kwargs['wa_message_id'] = wa_message_id
        return super(MailThread, self).message_post(**kwargs)
