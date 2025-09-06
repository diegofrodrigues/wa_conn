from odoo import http
from odoo.http import request


class WaWebhookController(http.Controller):
    def _resolve_account(self, raw, webhook_uuid=None):
        env = request.env
        Account = env['wa.account'].sudo()

        if webhook_uuid:
            acc = Account.search([('webhook_uuid', '=', webhook_uuid)], limit=1)
            if acc:
                return acc

        hdr_uuid = request.httprequest.headers.get('X-Webhook-UUID') or request.httprequest.headers.get('webhook_uuid')
        if hdr_uuid:
            acc = Account.search([('webhook_uuid', '=', hdr_uuid)], limit=1)
            if acc:
                return acc

        hdr_key = request.httprequest.headers.get('webhook_key')
        if hdr_key:
            acc = Account.search([('webhook_key', '=', hdr_key)], limit=1)
            if acc:
                return acc

        inst = (raw or {}).get('instance') or ((raw or {}).get('data') or {}).get('instance') or (raw or {}).get('name')
        if inst:
            acc = Account.search([('name', '=', inst)], limit=1)
            if acc:
                return acc
        return Account.browse()

    def _process_webhook(self, account, raw):
        if not account:
            return {'error': 'account_not_found'}

        # Validate secret header sent by provider (configured at instance creation)
        hdrs = request.httprequest.headers
        incoming_key = hdrs.get('webhook_key') or hdrs.get('X-Webhook-Key') or hdrs.get('Webhook-Key')
        expected_key = account.webhook_key
        # Require presence and exact match to avoid spoofed calls
        if not incoming_key or not expected_key or incoming_key != expected_key:
            return {'error': 'forbidden', 'reason': 'invalid_webhook_key'}

        return account.sudo().inbound_handle(raw, request=request)

    @http.route('/wa/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_webhook(self, **kwargs):
        raw = request.get_json_data() or {}
        account = self._resolve_account(raw)
        return self._process_webhook(account, raw)

    @http.route('/wa/webhook/<string:webhook_uuid>', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_webhook_uuid(self, webhook_uuid, **kwargs):
        raw = request.get_json_data() or {}
        account = self._resolve_account(raw, webhook_uuid=webhook_uuid)
        return self._process_webhook(account, raw)
