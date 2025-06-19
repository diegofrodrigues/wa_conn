from odoo import http
from odoo.http import request, Response


class BitconnWebhookController(http.Controller):
    url = '/webhook'
    @http.route(f'{url}', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_webhook(self, **kwargs):
        """Handle incoming webhook requests."""
        h = request.httprequest.headers
        json_data = request.get_json_data()
        print(json_data)
        print(h)

        if not json_data:
            return {'error': 'Invalid JSON data received.'}
        
        event_type = json_data.get('event')
        if not event_type:
            return {'error': 'Event type is missing in the JSON data.'}

        # Handle different event types
        if event_type == 'messages.upsert':
            return self.handle_messages_upsert(json_data)
        elif event_type == 'messages.update':
            return self.handle_messages_update(json_data)
        elif event_type == 'messages.delete':
            return self.handle_messages_delete(json_data)
        else:
            return {'error': f'Unhandled event type: {event_type}'}
        

    def handle_messages_upsert(self, json_data):
        """Handle the 'messages.upsert' event."""
        #message_content = json_data.get('message', 'No message provided')
        message_content = json_data['data']['message']['conversation']
        #channel_name = json_data.get('channel_name', 'General')
        channel_name = 'Administrator'

        # Extract values
        remote_jid = json_data['data']['key']['remoteJid']
        sender = json_data['sender']

        # Extract only numbers
        remote_jid_number = ''.join(char for char in remote_jid if char.isdigit())
        sender_number = ''.join(char for char in sender if char.isdigit())
        '''
        # Get the author (sender) using sender_numbers
        author = request.env['res.partner'].sudo().search([('mobile', '=', sender_number)], limit=1)
        if not author:
            return {'error': f'No matching author found for sender number: {sender_number}'}

        # Get the recipient using remote_jid_numbers
        recipient = request.env['res.partner'].sudo().search([('mobile', '=', remote_jid_number)], limit=1)
        if not recipient:
            return {'error': f'No matching recipient found for remote_jid number: {remote_jid_number}'}
        '''

        # Find or create the Discuss channel
        channel = request.env['discuss.channel'].sudo().search([('name', '=', 'Administrator')], limit=1)
        if not channel:
            channel = request.env['discuss.channel'].sudo().create({
                'name': channel_name,
                'author_id': 1,
                'channel_type': 'whatsapp',
                'channel_partner_ids': [(1)],
            })

        # Post a message to the channel
        channel.message_post(
            body=f"{message_content}",
            message_type='comment',
            subtype_xmlid="mail.mt_comment",
            author_id=2,
        )

        return {'success': True, 'message': 'Message posted successfully for messages.upsert.'}

    def handle_messages_update(self, json_data):
        """Handle the 'messages.update' event."""
        # Example logic for handling message updates
        message_id = json_data.get('message_id')
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


    @http.route(['/wa/webhook/<string:webhook_uuid>'], type='json', auth='public', methods=['POST'], csrf=False)
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
        self._process_webhook_event(wa_account, json_data)

        return {"status": "ok", "account_id": wa_account.id}

