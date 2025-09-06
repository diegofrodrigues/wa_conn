class NormalizedPayload:
    def __init__(self, **kw):
        self.provider = kw.get('provider')
        self.instance = kw.get('instance')
        self.event = kw.get('event')

        self.message_id = kw.get('message_id')
        self.remote_jid = kw.get('remote_jid')
        self.mobile = kw.get('mobile')

        self.from_me = bool(kw.get('from_me')) if kw.get('from_me') is not None else False
        self.push_name = kw.get('push_name')
        self.message = (kw.get('message') or '').strip()
        self.message_type = kw.get('message_type')
        self.mime_type = kw.get('mime_type')

        self.attachment_b64 = kw.get('attachment_b64')
        self.attachment_name = kw.get('attachment_name')

        self.raw = kw.get('raw') or {}

    def has_attachment(self):
        return bool(self.attachment_b64)

    def is_incoming(self):
        return not bool(self.from_me)

    def to_dict(self):
        return {
            'provider': self.provider,
            'instance': self.instance,
            'event': self.event,
            'message_id': self.message_id,
            'remote_jid': self.remote_jid,
            'mobile': self.mobile,
            'from_me': self.from_me,
            'push_name': self.push_name,
            'message': self.message,
            'message_type': self.message_type,
            'mime_type': self.mime_type,
            'attachment_b64': self.attachment_b64,
            'attachment_name': self.attachment_name,
            'raw': self.raw,
        }
