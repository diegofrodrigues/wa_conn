from odoo import _, api, fields, models
import requests
import base64
import time
import uuid
import secrets


class WAApiEvent(models.Model):
    _name = 'wa.api.event'
    _description = 'WhatsApp API Event'

    name = fields.Char(string="Event Name", required=True)


class WAAccount(models.Model):
    _name = 'wa.account'
    _description = 'WhatsApp Account'
    _inherit = ['mail.thread']

    name = fields.Char(string="Instance Name", required=True, tracking=True)
    api_url = fields.Char(string="API URL", required=True, tracking=True)
    api_key = fields.Char(string="API Key", required=True)
    state = fields.Selection(
        [('disconnected', 'Disconnected'), ('connected', 'Connected'), ('connecting', 'Connecting'), ('not_created', 'Not Created')],
        string="State",
        default='not_created',
        readonly=True,
        tracking=True,
        compute='_compute_state',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        help="The company this WhatsApp account belongs to."
    )
    qr_code = fields.Image(
        string="QR Code",
        help="QR Code for WhatsApp connection.",
        max_width=200,
        max_height=200,
        store=True,
        readonly=False,
    )

    reject_call = fields.Boolean(string="Reject Call", default=False)
    ignore_group = fields.Boolean(string="Ignore Group", default=False)
    always_online = fields.Boolean(string="Always Online", default=False)
    view_message = fields.Boolean(string="View Message", default=False)
    sync_history = fields.Boolean(string="Sync History", default=False)
    view_status = fields.Boolean(string="View Status", default=False)
    call_rejected_message = fields.Char(string="Call Rejected Message")

    webhook_url = fields.Char(string="Webhook URL", readonly=True, help="URL do webhook para receber eventos.")
    webhook_key = fields.Char(string="Webhook Key", readonly=True, help="Chave secreta do webhook.")
    webhook_uuid = fields.Char(string="Webhook UUID", readonly=True, help="UUID único do webhook.")

    api_events_ids = fields.Many2many(
        'wa.api.event',
        'wa_account_api_event_rel',
        'account_id',
        'event_id',
        string="API Events",
        help="API events associated with this account."
    )

    instance_created = fields.Boolean(
        string="Instance Created",
        default=False,
        help="Indicates whether the WhatsApp instance was successfully created."
    )

    enable_webhook = fields.Boolean(string="Enable Webhook", default=False)
    base64_webhook = fields.Boolean(string="Base64 Webhook", default=False)

    def get_url_text_message(self):
        self.ensure_one()
        return f"{self.api_url}/message/sendText/{self.name}"
    
    def get_url_media_message(self):
        self.ensure_one()
        return f"{self.api_url}/message/sendMedia/{self.name}"
    
    def get_headers(self):
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key,
        }
        return headers

    def connect(self):
        """
        Connect to the WhatsApp instance and retrieve the QR code if necessary.
        """
        self.ensure_one()
        self.check_status()
        if self.state == 'disconnected':
            pass
        elif self.state == 'connected':
            return
        
        url = f"{self.api_url}/instance/connect/{self.name}"
        try:
            response = requests.get(url, headers=self.get_headers())
            if response.status_code == 200:
                qr_code_data = response.json().get('base64')
                if qr_code_data:
                    self.qr_code = qr_code_data.split(",")[1]
                    self.state = 'connecting'  
            else:
                self.qr_code = False
                raise Exception(_(f"Failed to connect: {response.text}"))
        except Exception as e:
            self.qr_code = False
            raise Exception(_(f"Error while connecting: {str(e)}"))
        
    def restart(self):
        self.ensure_one()
        self.check_status()
        url = f"{self.api_url}/instance/restart/{self.name}"
        try:
            response = requests.put(url, headers=self.get_headers())
            if response.status_code == 200:
                print(response.text)
            elif response.status_code == 404:
                print(response.text)
            else:
                raise Exception(_(f"Failed to restart: {response.text}"))
        except Exception as e:
            self.qr_code = False
            raise Exception(_(f"Error: {str(e)}"))
        
    def disconnect(self):
        """
        Disconnect from the WhatsApp instance.
        """
        self.ensure_one()
        self.check_status()
        url = f"{self.api_url}/instance/logout/{self.name}"
        try:
            response = requests.delete(url, headers=self.get_headers())
            if response.status_code == 200:
                self.state = 'disconnected'
                print(response.text)
            elif response.status_code == 404:
                print(response.text)
            else:
                raise Exception(_(f"Failed to disconnect: {response.text}"))
        except Exception as e:
            self.qr_code = False
            raise Exception(_(f"Error: {str(e)}"))

    def check_status(self):
        """
        Check the status of the WhatsApp instance.
        """
        self.ensure_one()
        url = f"{self.api_url}/instance/connectionState/{self.name}"
        try:
            response = requests.get(url, headers=self.get_headers())
            if response.status_code == 200:
                instance_state = response.json().get('instance', {}).get('state')
                if instance_state == 'open':
                    self.state = 'connected'  
                elif instance_state == 'connecting': 
                    self.state = 'connecting' 
                else: 
                    self.state = 'disconnected'  
            else:
                raise Exception(_(f"Failed to check status: {response.text}"))
        except Exception as e:
            raise Exception(_(f"Error while checking status: {str(e)}"))

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override the create method to add custom logic when creating WhatsApp accounts.
        Supports batch creation.
        """
        for vals in vals_list:
            if 'name' in vals and 'company_id' in vals:
                existing_account = self.search([
                    ('name', '=', vals['name']),
                    ('company_id', '=', vals['company_id'])
                ])
                if existing_account:
                    raise ValueError(_("A WhatsApp account with this name already exists for the selected company."))

            if 'state' not in vals:
                vals['state'] = 'disconnected'
            if not vals.get('webhook_key'):
                vals['webhook_key'] = secrets.token_urlsafe(32)
            if not vals.get('webhook_uuid'):
                vals['webhook_uuid'] = str(uuid.uuid4())
            if not vals.get('webhook_url'):
                api_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
                vals['webhook_url'] = f"{api_url}/wa/webhook/{vals['webhook_uuid']}"

        accounts = super(WAAccount, self).create(vals_list)

        for account in accounts:
            account.message_post(body=_("WhatsApp account '%s' has been created." % account.name))

        return accounts

    def create_instance(self):
        self.ensure_one()
        # event_names = [event.name for event in self.api_events_ids]
        # if not event_names:
        #     event_names = ['APPLICATION_STARTUP','QRCODE_UPDATED']
        data = {
            "instanceName": self.name,
            "integration": "WHATSAPP-BAILEYS",
            "rejectCall": self.reject_call,
            "msgCall": self.call_rejected_message or '',
            "groupsIgnore": self.ignore_group,
            "alwaysOnline": self.always_online,
            "readMessages": self.view_message,
            "readStatus": self.view_status,
            "syncFullHistory": self.sync_history,
        }
        event_names = [event.name for event in self.api_events_ids]
        if not event_names:
            event_names = ['APPLICATION_STARTUP', 'QRCODE_UPDATED']
        if self.enable_webhook:
            data["webhook"] = {
                "url": self.webhook_url,
                "byEvents": False,
                "base64": self.bse64_webhook,
                "headers": {
                    "webhook_key": self.webhook_key
                },
                "events": event_names,
            }
    
        url = f"{self.api_url}/instance/create"
        try:
            response = requests.post(url, json=data, headers=self.get_headers())
            if response.status_code == 201:
                self.instance_created = True
                return
            else:
                raise Exception(_(f"Failed to create instance: {response.text}"))
        except Exception as e:
            raise Exception(_(f"Error while creating instance: {str(e)}"))
        
    def delete_instance(self):
        """
        Delete the WhatsApp instance and clear the QR code.
        """
        self.ensure_one()
        self.check_status()
        url = f"{self.api_url}/instance/delete/{self.name}"
        try:
            response = requests.delete(url, headers=self.get_headers())
            if response.status_code == 200:
                self.instance_created = False
                self.qr_code = False
                print(response.text)
            elif response.status_code == 404:
                print(response.text)
            else:
                raise Exception(_(f"Failed to delete: {response.text}"))
        except Exception as e:
            self.qr_code = False
            raise Exception(_(f"Error: {str(e)}"))
        
    def refresh_qrcode(self):
        self.connect()
        # TODO: add auto reload on receive webhook QRCODE_UPDATED event
        # return { 
        #     'type': 'ir.actions.client',
        #     'tag': 'reload',
        # }

    @api.depends('instance_created', 'state')
    def _compute_state(self):
        for rec in self:
            if not rec.instance_created:
                rec.state = 'not_created'
            elif rec.state == 'not_created':
                rec.state = 'disconnected'

