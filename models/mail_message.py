from odoo import _,api, fields, models
try:
    from odoo.tools import html2plaintext as _html2plaintext
except Exception:  # safe fallback
    def _html2plaintext(html):
        import re
        text = re.sub(r'<[^>]+>', '', html or '')
        return text.replace('&nbsp;', ' ').replace('&amp;', '&')


class Message(models.Model):
    _inherit = 'mail.message'

    message_type = fields.Selection(
        selection_add=[('whatsapp', 'whatsapp')],
        ondelete={'whatsapp': 'set default'}
    )
    message_derection = fields.Selection(
        [('input','iput'),
        ('output','output')],
        # compute ='_comput_message_direction'
    )
    wa_message_id = fields.Char()

    @api.depends('message_type')
    def _comput_message_direction(self):
        if self.message_derection == 'whatsapp':
            self.message_derection = 'output'

    is_wa = fields.Boolean(default=False, compute ='_compute_is_wa')

    @api.depends('message_type')
    def _compute_is_wa(self):
        if self.message_type == 'whatsapp':
            self.is_wa = True

    @api.model_create_multi
    def create(self, values_list):
        messages = super(Message, self).create(values_list)
        # Skip WA sending if explicitly requested (e.g., inbound webhook posts)
        if self.env.context.get('wa_skip_send'):
            return messages

        subtype_comment = self.env.ref('mail.mt_comment', raise_if_not_found=False)
        for message in messages:
            # Only handle messages posted on discuss.channel
            if message.model != 'discuss.channel' or not message.res_id:
                continue
            # Only send for allowed message types (comment or whatsapp)
            if message.message_type not in ('comment', 'whatsapp'):
                continue
            # Only send plain comments, ignore join/leave and other system subtypes
            if subtype_comment and message.subtype_id and message.subtype_id.id != subtype_comment.id:
                continue
            # Use sudo to avoid ACL errors when checking the channel, and ensure it exists
            channel = self.env['discuss.channel'].sudo().browse(message.res_id)
            if not channel.exists():
                continue
            # Only send WA for WA-enabled channels
            if not channel.is_wa:
                continue
            # Require an account to send
            account = channel.wa_account_id if 'wa_account_id' in channel._fields else None
            if not account:
                continue
            # Ensure the account-owner consistency if present in context (optional safety)
            ctx_acc = self.env.context.get('wa_account_id')
            if ctx_acc and int(ctx_acc) != account.id:
                continue
            # Determine direction: if the author is the WA partner, it's inbound; do not re-send
            if message.author_id and channel.wa_partner_id and message.author_id.id == channel.wa_partner_id.id:
                message.message_derection = 'input'
                continue

            # Outbound from Odoo to WA: send through account/provider
            try:
                # Convert HTML body to plaintext
                plain = (_html2plaintext(message.body or '') or '').strip()
                if message.attachment_ids:
                    for attachment in message.attachment_ids:
                        response = account.wa_send_media(
                            mobile=channel.wa_partner_id.mobile,
                            caption=plain,
                            b64=attachment.datas,
                            mime=attachment.mimetype or 'application/octet-stream',
                            filename=attachment.name,
                        )
                        message.message_derection = 'output'
                        try:
                            message.wa_message_id = response.get('id') or (response.get('raw') or {}).get('id')
                        except Exception:
                            pass
                else:
                    if not plain:
                        continue
                    response = account.wa_send_text(
                        mobile=channel.wa_partner_id.mobile,
                        message=plain,
                    )
                    message.message_derection = 'output'
                    try:
                        message.wa_message_id = response.get('id') or (response.get('raw') or {}).get('id')
                    except Exception:
                        pass
            except Exception:
                # swallow WA send errors to not break core message creation
                continue
        return messages
        
