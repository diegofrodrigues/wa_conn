from odoo import _, api, fields, models
import requests
import base64


class WAAccount(models.Model):
    _name = 'wa.account'
    _description = 'WhatsApp Account'
    _inherit = ['mail.thread']  # Add mail.thread mixin

    name = fields.Char(string="Instance Name", required=True, tracking=True)  # Enable tracking
    base_url = fields.Char(string="Base URL", required=True, tracking=True)
    api_key = fields.Char(string="API Key", required=True)
    state = fields.Selection(
        [('disconnected', 'Disconnected'), ('connected', 'Connected')],
        string="State",
        default='disconnected',
        readonly=True,
        tracking=True  # Enable tracking
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        help="The company this WhatsApp account belongs to."
    )

    def get_url_text_message(self):
        self.ensure_one()
        return f"{self.base_url}/message/sendText/{self.name}"
    
    def get_url_media_message(self):
        self.ensure_one()
        return f"{self.base_url}/message/sendMedia/{self.name}"

    def connect(self):
        """
        Connect to the WhatsApp instance and retrieve the QR code if necessary.
        """
        self.ensure_one()
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key,
        }
        url = f"{self.base_url}/instance/connect/{self.name}"
        try:
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                qr_code_data = response.json().get('qr_code')
                if qr_code_data:
                    self.qr_code = self._base64_to_image(qr_code_data)
                self.state = 'connected'
            else:
                raise Exception(f"Failed to connect: {response.text}")
        except Exception as e:
            raise Exception(f"Error while connecting: {str(e)}")

    def check_status(self):
        """
        Check the status of the WhatsApp instance.
        """
        self.ensure_one()
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key,
        }
        url = f"{self.base_url}/instance/status/{self.name}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                instance_state = response.json().get('instance', {}).get('state')
                self.state = 'connected' if instance_state == 'open' else 'disconnected'
            else:
                raise Exception(f"Failed to check status: {response.text}")
        except Exception as e:
            raise Exception(f"Error while checking status: {str(e)}")

    def _base64_to_image(self, b64_str):
        """
        Convert a base64 string to an image.
        """
        if "data:image" in b64_str:
            b64_str = b64_str.split(",")[1]
        return base64.b64decode(b64_str)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override the create method to add custom logic when creating WhatsApp accounts.
        Supports batch creation.
        """
        for vals in vals_list:
            # Ensure the name is unique for the company
            if 'name' in vals and 'company_id' in vals:
                existing_account = self.search([
                    ('name', '=', vals['name']),
                    ('company_id', '=', vals['company_id'])
                ])
                if existing_account:
                    raise ValueError(_("A WhatsApp account with this name already exists for the selected company."))

            # Set default state to 'disconnected' if not provided
            if 'state' not in vals:
                vals['state'] = 'disconnected'

        # Call the super method to create the records
        accounts = super(WAAccount, self).create(vals_list)

        # Log a message for each created account
        for account in accounts:
            account.message_post(body=_("WhatsApp account '%s' has been created." % account.name))

        return accounts

    def action_add_new_account(self):
        """
        Action to add a new WhatsApp account.
        Opens a new form view for creating a WhatsApp account.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': _('New WhatsApp Account'),
            'res_model': 'whatsapp.account',
            'view_mode': 'form',
            'target': 'new',
        }
