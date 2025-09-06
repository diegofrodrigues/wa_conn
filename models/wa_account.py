from odoo import _, api, fields, models
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
        [
            ('not_created', 'Not Created'),
            ('disconnected', 'Disconnected'),
            ('connecting', 'Connecting'),
            ('connected', 'Connected'),
        ],
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

    # Provider strategy
    provider = fields.Selection(
        [('evolution', 'Evolution'),
         ('unoapi', 'UnoAPI'),],  # adicione outros providers aqui
        required=True,
        default='evolution',
        tracking=True,
    )

    def _provider_model_name(self):
        self.ensure_one()
        mapping = {
            'evolution': 'wa.provider.evolution',
            'unoapi': 'wa.provider.unoapi',
        }
        model = mapping.get(self.provider)
        if not model:
            raise ValueError(f'Unsupported provider: {self.provider}')
        return model

    def _provider(self):
        return self.env[self._provider_model_name()]

    # ------------- Delegação para o provider -------------
    # Entrada (webhook)
    def normalize_inbound(self, raw, request=None):
        self.ensure_one()
        return self._provider().normalize_inbound(self, raw, request=request)

    # Saída
    def wa_send_text(self, mobile, message):
        self.ensure_one()
        return self._provider().send_text(self, mobile, message)

    def wa_send_media(self, mobile, *, caption='', b64=None, mime=None, filename=None):
        self.ensure_one()
        return self._provider().send_media(self, mobile, caption=caption, b64=b64, mime=mime, filename=filename)

    # ------------- Entrada completa (webhook -> ORM) -------------
    def inbound_handle(self, raw, request=None):
        """Delegação completa para o provider."""
        self.ensure_one()
        return self._provider().inbound_handle(self, raw, request=request)

    # Ciclo de vida/estado
    def create_instance(self):
        self.ensure_one()
        res = self._provider().create_instance(self)
        if res.get('ok'):
            self.instance_created = True
            if self.state == 'not_created':
                self.state = 'disconnected'
        else:
            raise Exception(_(f"Failed to create instance: {res.get('text') or res}"))
        return res

    def delete_instance(self):
        self.ensure_one()
        res = self._provider().delete_instance(self)
        if res.get('ok'):
            self.instance_created = False
            self.qr_code = False
            self.state = 'not_created'
        else:
            raise Exception(_(f"Failed to delete: {res.get('text') or res}"))
        return res

    def check_status(self):
        """
        Consulta o estado no provider e mapeia para o campo state.
        """
        self.ensure_one()
        res = self._provider().check_status(self)
        if res.get('ok'):
            state = (res.get('state') or '').lower()
            if state == 'open':
                self.state = 'connected'
            elif state == 'connecting':
                self.state = 'connecting'
            elif state in ('closed', 'logout', 'disconnected'):
                self.state = 'disconnected'
            # outros estados: manter como está
        return res

    def connect(self):
        """
        Solicita conexão e retorna QR code (se aplicável).
        """
        self.ensure_one()
        # tenta atualizar estado antes
        self.check_status()
        if self.state == 'connected':
            return {'ok': True, 'state': 'connected'}

        res = self._provider().connect(self)
        if res.get('ok') and res.get('qrcode_b64'):
            b64 = res['qrcode_b64']
            if isinstance(b64, str) and ',' in b64:
                b64 = b64.split(',', 1)[1]
            self.qr_code = b64
            self.state = 'connecting'
        elif not res.get('ok'):
            self.qr_code = False
            raise Exception(_(f"Failed to connect: {res.get('text') or res}"))
        return res

    def restart(self):
        self.ensure_one()
        res = self._provider().restart(self)
        if not res.get('ok'):
            raise Exception(_(f"Failed to restart: {res.get('text') or res}"))
        return res

    def disconnect(self):
        """
        Desconecta a instância.
        """
        self.ensure_one()
        res = self._provider().disconnect(self)
        if res.get('ok'):
            self.state = 'disconnected'
            self.qr_code = False
        else:
            raise Exception(_(f"Failed to disconnect: {res.get('text') or res}"))
        return res

    def refresh_qrcode(self):
        """
        Força a atualização do QR code (se suportado pelo provider).
        """
        return self.connect()

    def new_webhook_url(self):
        """
        Gera novas credenciais/URL do webhook.
        """
        new_key = secrets.token_urlsafe(32)
        new_uuid = str(uuid.uuid4())
        api_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        self.webhook_key = new_key
        self.webhook_uuid = new_uuid
        self.webhook_url = f"{api_url}/wa/webhook/{new_uuid}"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override do create para inicializar campos e garantir unicidade por empresa.
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

    @api.depends('instance_created', 'state')
    def _compute_state(self):
        for rec in self:
            if not rec.instance_created:
                rec.state = 'not_created'
            elif rec.state == 'not_created':
                rec.state = 'disconnected'
