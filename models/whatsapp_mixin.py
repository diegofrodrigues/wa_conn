from odoo import _, models
import requests
from odoo.tools import html2plaintext
from ..tools.util import get_media_type, get_mime_type


class WhatsAppMixin(models.AbstractModel):
    _name = 'whatsapp.mixin'
    _description = 'WhatsApp Mixin'

    def send_whatsapp(self, mobile, message, media=None, media_filename=None, res_model=None, res_id=None, whatsapp_account_id=None):
        """
        Send a WhatsApp message using the specified WhatsApp account.
        :param mobile: Recipient's mobile number.
        :param message: Message text (HTML or plain text).
        :param media: Base64-encoded media file (optional).
        :param media_filename: Filename of the media file (optional).
        :param res_model: Model to link the message to (optional).
        :param res_id: Record ID to link the message to (optional).
        :param whatsapp_account_id: ID of the WhatsApp account to use.
        """
        whatsapp_account = self.env['whatsapp.account'].browse(whatsapp_account_id)
        if not whatsapp_account:
            raise ValueError("Invalid WhatsApp account specified.")

        # Convert HTML message to plain text if necessary
        if message and ('<' in message and '>' in message):
            message = html2plaintext(message)

        headers = {
            'Content-Type': 'application/json',
            'apikey': whatsapp_account.api_key,
        }

        if media:
            url = whatsapp_account.get_url_media_message()
            media_decoded = media.decode()
            media_type = get_media_type(media_filename)
            mime_type = get_mime_type(media_filename)
            payload = {
                'number': f'+{mobile}',
                'caption': message,
                'mediatype': media_type,
                'mimetype': mime_type,
                'media': media_decoded,
                'fileName': media_filename,
            }
        else:
            url = whatsapp_account.get_url_text_message()
            payload = {
                'number': f'+{mobile}',
                'text': message,
            }

        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 201:
                whatsapp_icon = '<i class="fa fa-whatsapp" style="color:green;"></i>'
                message_body = f'{whatsapp_icon} {message}'
                if media:
                    # Save the media file as an attachment
                    attachment = self.env['ir.attachment'].create({
                        'name': media_filename,
                        'type': 'binary',
                        'datas': media,
                        'res_model': res_model,
                        'res_id': res_id,
                        'mimetype': mime_type,
                    })
                    # Add a preview for the file
                    if mime_type.startswith('image/'):
                        message_body += f'<br/><img src="/web/content/{attachment.id}" alt="{media_filename}" style="max-width: 300px; max-height: 300px;"/>'
                    else:
                        message_body += f'<br/><a href="/web/content/{attachment.id}" target="_blank">{media_filename}</a>'
                self.env['mail.message'].create({
                    'body': message_body,
                    'model': res_model,
                    'res_id': res_id,
                })
            else:
                whatsapp_icon = '<i class="fa fa-whatsapp" style="color:red;"></i>'
                self.env['mail.message'].create({
                    'body': f'{whatsapp_icon} {response.text}',
                    'model': res_model,
                    'res_id': res_id,
                })
        except Exception as e:
            self.env['mail.message'].create({
                'body': f'Error while sending WhatsApp message: {str(e)}',
                'model': res_model,
                'res_id': res_id,
            })
