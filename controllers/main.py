import requests as rq
from odoo import http
from odoo.http import request, Response
import datetime
import base64
from odoo.tools import image


# from ..plugins.normalizer import Normalizer
from ..plugins.base import get_plugin
from ..plugins.providers import *  # garante registro

'''
class Payload(object):
    message = ''
    instance = None
    event = None
    push_name = None
    mobile = None
    partner = None
    attachment = None
    attachment_name = None
    message_type = None
    mime_type = None
    message_id = None
    from_me = None
    remote_jid = None

    def __init__(self, raw):
        self.raw = raw or {}
        self.data = self.raw.get('data') or {}
        key = self.data.get('key') or {}

        # topo
        self.instance = self.raw.get('instance')
        self.event = self.raw.get('event')

        # ids e remetente (tentando múltiplas origens)
        self.remote_jid = key.get('remoteJid') or self.data.get('remoteJid') or self.raw.get('sender')
        self.message_id = key.get('id') or self.data.get('messageId') or self.data.get('keyId')
        self.from_me = key.get('fromMe') if key else self.data.get('fromMe')
        self.push_name = self.data.get('pushName')

        # mobile
        self.mobile = self._extract_mobile(self.remote_jid)

        # mensagem (só existe em upsert, normalmente)
        msg_dict = self.data.get('message') if isinstance(self.data.get('message'), dict) else {}
        self.message_type = self.data.get('messageType') or (next(iter(msg_dict)) if msg_dict else None)
        self.message = self._extract_text(msg_dict, self.message_type)
        self.mime_type = self._extract_mime_type(msg_dict, self.message_type)
        self.attachment = self._extract_attachment_b64(msg_dict)
        self.attachment_name = self._build_attachment_name(self.mime_type)

        # cria/obtém partner apenas em upsert
        if self.event == 'messages.upsert' and self.mobile:
            self.partner = self._get_or_create_partner()

    # -------- helpers seguros --------
    def _extract_mobile(self, remote_jid):
        if not remote_jid:
            return None
        return str(remote_jid).split('@', 1)[0]

    def _extract_text(self, message_dict, msg_type):
        if not message_dict:
            return ''
        if isinstance(message_dict.get('conversation'), str):
            return message_dict.get('conversation')
        etm = message_dict.get('extendedTextMessage') or {}
        if isinstance(etm.get('text'), str) and etm.get('text').strip():
            return etm.get('text').strip()
        payload = message_dict.get(msg_type) or {}
        for k in ('caption', 'text'):
            val = payload.get(k)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return ''

    def _extract_mime_type(self, message_dict, msg_type):
        payload = message_dict.get(msg_type) or {}
        mt = payload.get('mimetype')
        return mt if isinstance(mt, str) and '/' in mt else None

    def _extract_attachment_b64(self, message_dict):
        b64 = message_dict.get('base64')
        return b64 if isinstance(b64, str) and b64 else None

    def _build_attachment_name(self, mime_type):
        if not mime_type:
            return None
        kind = mime_type.split('/', 1)[0]
        now = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        prefix = {'image': 'Image', 'video': 'Video', 'audio': 'Voice'}.get(kind, 'File')
        ext = {'image': '.jpeg', 'video': '.mp4', 'audio': '.mp3'}.get(kind, '.bin')
        return f'{prefix}-{now}{ext}'

    def _get_or_create_partner(self):
        Partner = request.env['res.partner'].sudo()
        partner = Partner.search([('mobile', '=', self.mobile)], limit=1)
        if not partner:
            partner = Partner.create({'name': self.push_name or self.mobile, 'mobile': self.mobile})
        return partner
'''


class Payload(object):
    message = None
    instance = None
    event = None
    push_name = None
    mobile = None
    partner = None
    attachment = None
    attachment_name = None
    message_type = None
    mime_type = None
    message_id = None
    from_me = None
    remote_jid = None

    def __init__(self, data_dict):
        print(data_dict)
        self.raw = data_dict
        self.event = self.raw.get('event')
        self.instance = self.raw.get('instance')
        self.data = self.raw.get('data')
        self.key = self.data.get('key')
        self.remote_jid = self._get_remote_jid()
        self.mobile = str(self.remote_jid.split('@')[0])
        self.push_name = self._get_push_name()

        self.partner = self._get_or_create_partner()
        self.message_type = self._get_message_type() #self.data['messageType'] or None
        self.message_id = self._get_message_id() #self.data['key']['id']
        self.mime_type = self._get_mime_type()
        self.message = self._get_message()
        self.attachment = self._get_attachment()
        self.attachment_name = self._get_attachment_name()
        self.from_me = self._get_for_me() #self.data['key']['fromMe']
    
    def _get_remote_jid(self):
        if self.event == 'messages.update':
            self.remote_jid = self.data.get('remoteJid')
        elif self.event == 'messages.upsert':
            self.remote_jid = self.key.get('remoteJid')
        else:
            self.remote_jid = 'test@test'
        return self.remote_jid
    
    def _get_push_name(self): 
        if self.data == 'messages.upsert':
            self.push_name = self.data.get('pushName')
        return self.push_name
    
    def _get_for_me(self):
        if self.event == 'messages.upsert':
            self.from_me = self['key']['fromMe']
        return self.from_me

    def _get_or_create_partner(self):
        self.partner = request.env['res.partner'].sudo().search([('mobile', '=', self.mobile)], limit=1)
        if not self.partner:
            self.partner.sudo().create({
                'name': self.push_name,
                'mobile': self.mobile,
            })
        return self.partner

    def _get_message_type(self):
        if self.event == 'messages.upsert':
            self.message_type = self.data.get('messageType')
        return self.message_type
    
    def _get_message_id(self):
        if self.event == 'messages.upsert':
            self.message_id = self.data.get('key').get('id')
        return self.message_id
        
    def _get_message(self):
        if self.event == 'messages.upsert':
            if 'conversation' in self.data.get('message'):
                self.message = self.data['message']['conversation']
            elif 'caption' in self.data['message'][self.message_type]:
                self.message = self.data['message'][self.message_type]['caption']
            else:
                self.message = ''
        return self.message
     
    def _get_attachment(self):
        if self.event == 'messages.upsert':

            

            message_dict = self.data.get('message')
            if 'base64' in message_dict:
                self.attachment = self.data['message']['base64']
        return self.attachment

    def _get_mime_type(self):
        if self.event == 'messages.upsert':
        #if 'mimetype' in self.data.get('message').get(self.message_type):
            self.mime_type = self.data['message'][self.message_type]['mimetype']
        return self.mime_type
    
    def _get_attachment_name(self):
        if self.mime_type:
            attachment_type = self.mime_type.split('/')[0]
            time_stamp = str(datetime.datetime.now()).split(' ')
            dinamyc_name = time_stamp[0] + '-' + time_stamp[1].split('.')[1]
            if attachment_type == 'image':
                self.attachment_name = 'Image-' + dinamyc_name + '.jpeg'
            if attachment_type == 'video':
                self.attachment_name = 'Video-' + dinamyc_name + '.mp4'
            if attachment_type == 'audio':
                self.attachment_name = 'Voice-' + dinamyc_name + '.mp3'
            return self.attachment_name

class LeadWebhookController(http.Controller):
    url = '/webhook'
    @http.route(f'{url}', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_webhook(self, **kwargs):
        """Handle incoming webhook requests."""
        # headers = request.httprequest.headers
        data_dict = request.get_json_data()
        payload_obj = Payload(request.get_json_data())
        print(type(data_dict))
        print(data_dict)
        if not payload_obj:
            return {'error': 'Invalid JSON data received.'}
        
        event_type = payload_obj.event
        if not event_type:
            return {'error': 'Event type is missing in the JSON data.'}
        
        # Handle different event types
        if event_type == 'messages.upsert':
            return self.handle_messages_upsert(payload_obj)
        elif event_type == 'messages.update':
            return self.handle_messages_update(payload_obj)
        elif event_type == 'messages.delete':
            return self.handle_messages_delete(payload_obj)
        else:
            return {'error': f'Unhandled event type: {event_type}'}  

    def get_or_create_channel(self, partner):
        Channel = request.env['discuss.channel'].sudo()
        channel = Channel.search([('wa_partner_id', '=', partner.id)], limit=1)
        if not channel:
            avatar = partner.image_1920 or False
            vals = {
                'name': partner.name,
                'channel_type': 'channel',
                'is_wa': True,
                'wa_partner_id': partner.id,
                'avatar_128': partner.avatar_128,
                'stage_id': 1,
                #'channel_partner_ids': ['4',], #TODO: add logic of member on create 
                #'channel_member_ids' : ['4',], #TODO: add logic of member on create
            }
            if avatar:
                vals['image_128'] = avatar
            channel = Channel.create(vals)
        return channel

    def handle_messages_upsert(self, obj):
        """Handle the 'messages.upsert' event."""
        partner = obj.partner
        message = obj.message
        mixin = request.env['wa.mixin']
        avatar = mixin.sudo().get_profile_image(
            remote_jid = obj.remote_jid,
            whatsapp_account_id = 1, #TODO: add logic wa_account
        )
        if avatar:
            partner.sudo().write({
                'image_1920': avatar,
                })
        channel = self.get_or_create_channel(partner)
        Member = request.env['discuss.channel.member'].sudo()
        if not channel.channel_member_ids.filtered(lambda m: m.partner_id.id == partner.id):
            Member.create({'channel_id': channel.id, 'partner_id': partner.id})

        if channel:
            if obj.attachment:
                # Pass base64 directly; strip data URI prefix if present
                b64 = obj.attachment
                if isinstance(b64, str) and b64.strip().startswith('data:') and ',' in b64:
                    b64 = b64.split(',', 1)[1]
                msg = channel.with_context(wa_skip_send=True).sudo().message_post(
                    body=message,
                    message_type='whatsapp',
                    subtype_xmlid="mail.mt_comment",
                    author_id=partner.id,
                    attachments=[(obj.attachment_name, b64)],
                )
                for attachment in msg.attachment_ids:
                    mt = (attachment.mimetype or '').lower()
                    if mt in ('audio/mpeg', 'audio/mp3'):
                        request.env['discuss.voice.metadata'].sudo().create({'attachment_id': attachment.id})
            else:
               msg = channel.with_context(wa_skip_send=True).sudo().message_post(
                    body=message,
                    message_type='whatsapp',
                    subtype_xmlid="mail.mt_comment",
                    author_id=partner.id,
                )
            if msg:
                msg.write({
                    'wa_message_id': obj.message_id,
                    'message_derection': 'input',
                    })
            return msg
    

    def handle_messages_update(self, obj):
        """Handle the 'messages.update' event."""
        # Example logic for handling message updates
        print(obj)
        url = "https://evo-api.bitconn.com.br/chat/findMessages/bitconn"

        payload = { "where": { "key": { "id": "3EB0B12886208EE7D2D272" } } }
        headers = {
            "apikey": "429683c4c977415caafcce10f7d57e88",
            "Content-Type": "application/json"
        }

        response = rq.post(url, json=payload, headers=headers)

        print('result:####',response.json())
        message_id = obj.message_id
        if not message_id:
            return {'error': 'Message ID is missing for messages.update.'}

        # Perform your update logic here
        print(f"Updating message with ID: {message_id}")
        return {'success': True, 'message': f'Message with ID {message_id} updated successfully.'}

    def handle_messages_delete(self, json_data):
        """Handle the 'messages.delete' event."""
        # Example logic for handling message deletions
        message_id = json_data.get('message_id')
        if not message_id:
            return {'error': 'Message ID is missing for messages.delete.'}

        # Perform your delete logic here
        print(f"Deleting message with ID: {message_id}")
        return {'success': True, 'message': f'Message with ID {message_id} deleted successfully.'}

class WAAccountWebhookController(http.Controller):
    def _process_webhook_event(self, wa_account, json_data):
        """
        Processa eventos recebidos no webhook.
        Se event == 'qrcode.updated', atualiza o campo qr_code do wa_account com data.base64.
        """
        if json_data.get('event') == 'qrcode.updated':
            base64_img = json_data['data']['qrcode']['base64']
            print(base64_img)
            if base64_img and wa_account:
                base64_img = base64_img.split(",")[1]
                wa_account.qr_code = base64_img


    @http.route(['/v1/wa/webhook/<string:webhook_uuid>'], type='json', auth='public', methods=['POST'], csrf=False)
    def wa_webhook_dynamic(self, webhook_uuid, **kwargs):

        wa_account = request.env['wa.account'].sudo().search([('webhook_uuid', '=', webhook_uuid)], limit=1)
        if not wa_account or not wa_account.webhook_url or not wa_account.webhook_url.endswith(webhook_uuid):
            print('404')
            return Response("Account not found", status=404)
        
        received_key = request.httprequest.headers.get('Webhook-Key')
        if not received_key or received_key != wa_account.webhook_key:
            print('403')
            return Response("Invalid webhook key", status=403)
        
        json_data = request.get_json_data()
        print(json_data)
        self._process_webhook_event(wa_account, json_data)

        return {"status": "ok", "account_id": wa_account.id}

        # def get_or_create_lead(self, partner):
        #     lead = request.env['crm.lead'].sudo().search([('partner_id','=', partner.id)], limit=1)
        #     if not lead:
        #         lead.sudo().create({
        #             'name':'Nova oportunidade - '+ partner.name,
        #             'type':'opportunity',
        #             'user_id':'',
        #             'partner_id':partner.id,
        #         })
        #     return lead

        # def get_or_create_partner(self, obj):
        #     partner = request.env['res.partner'].sudo().search([('mobile','=', obj.mobile)], limit=1)
        #     if not partner:
        #         partner.sudo().create({
        #             'name': obj.push_name,
        #             'mobile': obj.mobile,
        #         })
        #     return partner

        #lead = self.get_or_create_lead(partner)
        # create lead or message
        # if lead:
        #     if attachment:
        #         attachment = request.env['ir.attachment'].sudo().create({
        #             'name': 'media_filename',
        #             'type': 'binary',
        #             'datas': attachment,
        #             'res_model': 'crm.lead',
        #             'res_id': lead.id,
        #             'mimetype': mimetype,
        #         })
        #         request.env['mail.message'].sudo().create({
        #             'body': message,
        #             'model': 'crm.lead',
        #             'res_id': lead.id,
        #             'author_id': partner.id,
        #             'attachment_ids': [attachment.id],
        #         })
                
        #     else:
        #         request.env['mail.message'].sudo().create({
        #             'body': message,
        #             'model': 'crm.lead',
        #             'res_id': lead.id,
        #             'author_id': partner.id,
        #         })
