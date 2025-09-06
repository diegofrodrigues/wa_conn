import base64
import requests
from ...tools.util import get_media_type, get_mime_type
from odoo import models


class NormalizerEvolution:
    """
    Evolution-specific normalizer.
    Converts the raw payload into a list of standardized NormalizedPayloads (DTOs).
    """
    def __init__(self, account):
        self.account = account

    def _strip_data_uri(self, b64):
        if isinstance(b64, str):
            s = b64.strip()
            if s.startswith('data:') and ',' in s:
                return s.split(',', 1)[1]
        return b64

    def _mime_from_data_uri(self, b64):
        if isinstance(b64, str):
            s = b64.strip()
            if s.startswith('data:'):
                rest = s[5:]
                return (rest.split(';', 1)[0] or None) if rest else None
        return None

    def _g(self, d, *keys):
        for k in keys:
            if isinstance(d, dict) and k in d:
                return d.get(k)
        return None

    def _from_nested_message(self, d):
        message_dict = self._g(d, 'message') or self._g(d, 'msg') or self._g(d, 'content') or {}
        out = {'text': None, 'mime': None, 'b64': None, 'filename': None, 'type': None}
        if not isinstance(message_dict, dict):
            return out

        if isinstance(message_dict.get('conversation'), str):
            out['text'] = message_dict.get('conversation')

        for key in ('extendedTextMessage', 'textMessage'):
            sub = message_dict.get(key)
            if isinstance(sub, dict):
                if not out['text']:
                    out['text'] = sub.get('text') or sub.get('caption')
                if key in ('extendedTextMessage', 'textMessage'):
                    out['type'] = out['type'] or 'text'

        if isinstance(message_dict.get('base64'), str) and message_dict.get('base64'):
            out['b64'] = out['b64'] or message_dict.get('base64')
        if isinstance(message_dict.get('mimetype'), str) and '/' in message_dict.get('mimetype'):
            out['mime'] = out['mime'] or message_dict.get('mimetype')
        for name_key in ('fileName', 'filename', 'name'):
            if message_dict.get(name_key):
                out['filename'] = out['filename'] or message_dict.get(name_key)

        media_keys = [
            ('imageMessage', 'image'), ('videoMessage', 'video'), ('audioMessage', 'audio'),
            ('documentMessage', 'document'), ('stickerMessage', 'sticker'), ('mediaMessage', 'document'), ('fileMessage', 'document'),
        ]
        for key, mtype in media_keys:
            sub = message_dict.get(key)
            if isinstance(sub, dict):
                out['mime'] = out['mime'] or sub.get('mimetype') or sub.get('mime_type')
                out['filename'] = out['filename'] or sub.get('fileName') or sub.get('filename') or sub.get('name')
                out['b64'] = out['b64'] or sub.get('base64') or sub.get('file_b64') or sub.get('media')
                if not out['text']:
                    out['text'] = sub.get('caption') or ''
                out['type'] = out['type'] or mtype

        return out

    def _normalize_one_dict(self, raw, data):
        g = self._g
        nested = self._from_nested_message(data)

        event = g(raw, 'event') or g(data, 'type') or 'messages.upsert'
        key = g(data, 'key') or {}
        message_id = g(data, 'message_id', 'id') or g(key, 'id')

        rjid = g(data, 'remoteJid', 'from') or g(key, 'remoteJid')
        remote_jid = str(rjid) if rjid else None
        mobile = remote_jid.split('@', 1)[0] if remote_jid else None

        from_me = bool(g(data, 'from_me') or g(key, 'fromMe') or False)
        # Captura tanto snake_case quanto camelCase e aliases comuns
        push_name = g(data, 'push_name', 'pushName', 'senderName', 'contact')

        message_text = g(data, 'text') or g(data, 'caption') or nested['text']
        if isinstance(message_text, dict):
            message_text = g(message_text, 'conversation', 'caption', 'text')
        if not isinstance(message_text, str):
            message_text = ''
        message = message_text.strip()

        mime_type = g(data, 'mimetype', 'mime_type') or nested['mime']
        attachment_b64 = g(data, 'base64', 'file_b64', 'media') or nested['b64']
        attachment_name = g(data, 'filename', 'name', 'fileName') or nested['filename']

        if attachment_b64:
            if not mime_type:
                mime_type = self._mime_from_data_uri(attachment_b64) or mime_type
            attachment_b64 = self._strip_data_uri(attachment_b64)

        msg_type = nested['type'] or ('document' if attachment_b64 else 'text')
        if not attachment_b64 and not message:
            msg_type = 'text'

        return {
            'provider': 'evolution',
            'instance': self.account.name,
            'event': event,
            'message_id': message_id,
            'remote_jid': remote_jid,
            'mobile': mobile,
            'from_me': from_me,
            'push_name': push_name,
            'message': message,
            'message_type': msg_type,
            'mime_type': mime_type,
            'attachment_b64': attachment_b64,
            'attachment_name': attachment_name,
            'raw': raw,
        }

    def normalize(self, raw):
        from ..dto import NormalizedPayload  # lazy import
        raw = raw or {}
        data = raw.get('data') or raw
        batch = data.get('messages') or data.get('events') or data.get('entries')
        items = []
        if isinstance(batch, list):
            for item in batch:
                nd = self._normalize_one_dict(raw, item or {})
                items.append(NormalizedPayload(**nd))
            return items
        nd = self._normalize_one_dict(raw, data or {})
        return [NormalizedPayload(**nd)]


class WAProviderEvolution(models.AbstractModel):
    _name = 'wa.provider.evolution'
    _description = 'WhatsApp Provider: Evolution'
    _inherit = 'wa.provider.base'

    def _headers(self, account):
        return {"Content-Type": "application/json", "apikey": account.api_key}

    def _fmt_number(self, mobile):
        m = str(mobile or '').strip().lstrip('+')
        return f'+{m}' if m else None

    def normalize_inbound(self, account, raw, request=None):
        normalizer = NormalizerEvolution(account)
        return normalizer.normalize(raw)

    def inbound_handle(self, account, raw, request=None):
        dto_items = self.normalize_inbound(account, raw, request=request) or []
        if not isinstance(dto_items, list):
            dto_items = [dto_items]
        if not dto_items:
            return {'status': 'ignored', 'reason': 'empty'}

        results = []
        env = self.env
        Partner = env['res.partner'].sudo()
        Channel = env['discuss.channel'].sudo()

        for dto in dto_items:
            event = (getattr(dto, 'event', '') or '').lower()
            if event != 'messages.upsert':
                results.append({'status': 'ignored', 'event': event or None})
                continue

            mobile = (getattr(dto, 'mobile', '') or '').strip()
            if not mobile:
                results.append({'status': 'ignored', 'reason': 'no_mobile'})
                continue

            push_name = getattr(dto, 'push_name', None)
            partner = Partner.wa_get_or_create_by_mobile(mobile, name=push_name)

            try:
                channel = partner.wa_get_or_create_channel(account=account)
            except Exception:
                domain = [('is_wa', '=', True), ('wa_partner_id', '=', partner.id)]
                if 'wa_account_id' in Channel._fields:
                    domain.append(('wa_account_id', '=', account.id))
                channel = Channel.search(domain, limit=1)
                if not channel:
                    vals = {
                        'name': partner.name,
                        'channel_type': 'channel',
                        'is_wa': True,
                        'wa_partner_id': partner.id,
                    }
                    if 'wa_account_id' in Channel._fields:
                        vals['wa_account_id'] = account.id
                    channel = Channel.create(vals)

            try:
                rjid = getattr(dto, 'remote_jid', None) or mobile
                img_b64 = self.get_profile_image(account, remote_jid=rjid)
                if img_b64:
                    if isinstance(img_b64, (bytes, bytearray)):
                        img_b64 = img_b64.decode()
                    if not partner.image_1920:
                        partner.sudo().write({'image_1920': img_b64})
                    vals_img = {}
                    if 'avatar_128' in channel._fields:
                        vals_img['avatar_128'] = img_b64
                    if 'image_128' in channel._fields:
                        vals_img['image_128'] = img_b64
                    if vals_img:
                        channel.sudo().write(vals_img)
            except Exception:
                pass

            mid = getattr(dto, 'message_id', None)
            if mid:
                existing = env['mail.message'].sudo().search([
                    ('model', '=', 'discuss.channel'),
                    ('res_id', '=', channel.id),
                    ('wa_message_id', '=', mid),
                ], limit=1)
                if existing:
                    results.append({'status': 'duplicate', 'channel_id': channel.id, 'msg_id': existing.id})
                    continue

            msg = channel.wa_post_incoming(dto, partner)
            results.append({'status': 'ok', 'channel_id': channel.id, 'msg_id': msg.id if msg else False})

        return {'results': results}

    def send_text(self, account, mobile, message):
        number = self._fmt_number(mobile)
        if not number:
            return {'ok': False, 'error': 'invalid_mobile'}

        url = f"{account.api_url}/message/sendText/{account.name}"
        payload = {'number': number, 'text': message or ''}

        resp = requests.post(url, json=payload, headers=self._headers(account), timeout=20)
        ok = 200 <= resp.status_code < 300
        try:
            data = resp.json()
        except Exception:
            data = {'text': resp.text}
        return {
            'ok': ok,
            'id': data.get('id') or data.get('message_id'),
            'raw': data,
            'status_code': resp.status_code,
        }

    def send_media(self, account, mobile, *, caption='', b64=None, mime=None, filename=None):
        number = self._fmt_number(mobile)
        if not number:
            return {'ok': False, 'error': 'invalid_mobile'}

        media_b64 = b64
        if isinstance(media_b64, (bytes, bytearray)):
            media_b64 = media_b64.decode()
        elif isinstance(media_b64, str):
            media_b64 = media_b64
        else:
            media_b64 = ''
        if not media_b64:
            return {'ok': False, 'error': 'empty_media'}

        eff_mime = mime or (get_mime_type(filename) if filename else None) or 'application/octet-stream'
        mt_root = get_media_type(filename) if filename else None
        if mt_root not in ('image', 'video', 'audio'):
            mt_root = 'document'

        url = f"{account.api_url}/message/sendMedia/{account.name}"
        payload = {
            'number': number,
            'caption': caption or '',
            'mediatype': mt_root,
            'mimetype': eff_mime,
            'media': media_b64,
            'fileName': filename or 'file.bin',
        }

        resp = requests.post(url, json=payload, headers=self._headers(account), timeout=40)
        ok = 200 <= resp.status_code < 300
        try:
            data = resp.json()
        except Exception:
            data = {'text': resp.text}
        return {
            'ok': ok,
            'id': data.get('id') or data.get('message_id'),
            'raw': data,
            'status_code': resp.status_code,
        }

    def create_instance(self, account):
        data = {
            "instanceName": account.name,
            "integration": "WHATSAPP-BAILEYS",
            "rejectCall": account.reject_call,
            "msgCall": account.call_rejected_message or '',
            "groupsIgnore": account.ignore_group,
            "alwaysOnline": account.always_online,
            "readMessages": account.view_message,
            "readStatus": account.view_status,
            "syncFullHistory": account.sync_history,
        }

        events = [e.name for e in account.api_events_ids] or ['APPLICATION_STARTUP', 'QRCODE_UPDATED']
        if account.enable_webhook:
            data["webhook"] = {
                "url": account.webhook_url,
                "byEvents": bool(events),
                "base64": bool(account.base64_webhook),
                "headers": {"webhook_key": account.webhook_key},
                "events": events,
            }

        url = f"{account.api_url}/instance/create"
        resp = requests.post(url, json=data, headers=self._headers(account), timeout=30)
        ok = resp.status_code in (200, 201)
        j = None
        try:
            j = resp.json()
        except Exception:
            j = None
        return {'ok': ok, 'status_code': resp.status_code, 'text': resp.text, 'json': j}

    def delete_instance(self, account):
        url = f"{account.api_url}/instance/delete/{account.name}"
        resp = requests.delete(url, headers=self._headers(account), timeout=20)
        ok = 200 <= resp.status_code < 300
        return {'ok': ok, 'status_code': resp.status_code, 'text': resp.text}

    def check_status(self, account):
        url = f"{account.api_url}/instance/connectionState/{account.name}"
        resp = requests.get(url, headers=self._headers(account), timeout=15)
        if resp.status_code != 200:
            return {'ok': False, 'error': resp.text, 'status_code': resp.status_code}
        try:
            data = resp.json()
        except Exception:
            return {'ok': False, 'error': resp.text, 'status_code': resp.status_code}
        state = (data.get('instance') or {}).get('state')
        return {'ok': True, 'state': state, 'status_code': resp.status_code}

    def connect(self, account):
        url = f"{account.api_url}/instance/connect/{account.name}"
        resp = requests.get(url, headers=self._headers(account), timeout=20)
        ok = 200 <= resp.status_code < 300
        b64 = None
        try:
            b64 = resp.json().get('base64')
        except Exception:
            b64 = None
        return {'ok': ok, 'qrcode_b64': b64, 'text': resp.text, 'status_code': resp.status_code}

    def restart(self, account):
        headers = self._headers(account)
        base = account.api_url.rstrip('/')
        name = account.name

        attempts = [
            ('put', f"{base}/instance/restart/{name}", None, None),
            ('post', f"{base}/instance/restart/{name}", None, None),
            ('post', f"{base}/instance/restart", {'instanceName': name}, 'json'),
            ('get', f"{base}/instance/restart/{name}", None, None),
        ]

        last = None
        for method, url, payload, kind in attempts:
            try:
                if method == 'put':
                    resp = requests.put(url, headers=headers, timeout=20)
                elif method == 'post':
                    if kind == 'json':
                        resp = requests.post(url, json=payload, headers=headers, timeout=20)
                    else:
                        resp = requests.post(url, headers=headers, timeout=20)
                elif method == 'get':
                    resp = requests.get(url, headers=headers, timeout=20)
                else:
                    continue
            except Exception as e:
                last = {'ok': False, 'status_code': 0, 'text': str(e)}
                continue

            ok = 200 <= resp.status_code < 300
            last = {'ok': ok, 'status_code': resp.status_code, 'text': resp.text}
            if ok:
                return last

        return last or {'ok': False, 'status_code': 0, 'text': 'restart failed: no endpoint accepted'}

    def disconnect(self, account):
        url = f"{account.api_url}/instance/logout/{account.name}"
        resp = requests.delete(url, headers=self._headers(account), timeout=20)
        ok = 200 <= resp.status_code < 300
        return {'ok': ok, 'status_code': resp.status_code, 'text': resp.text}

    def get_profile_image(self, account, remote_jid=None):
        if not remote_jid:
            return False
        headers = self._headers(account)
        url = f"{account.api_url}/chat/fetchProfilePictureUrl/{account.name}"
        try:
            # Converte JID para número
            num = str(remote_jid)
            if '@' in num:
                num = num.split('@', 1)[0]
            # aplica formatação com +
            if num and not num.startswith('+'):
                num = f'+{num}'
            r = requests.post(url, json={'number': num}, headers=headers, timeout=15)
            data = r.json()
            pic_url = data.get('profilePictureUrl')
            if not pic_url:
                return False
            img = requests.get(pic_url, timeout=20)
            if img.status_code == 200:
                return base64.b64encode(img.content)
        except Exception:
            return False
        return False
