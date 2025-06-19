from odoo import _, api, fields, models
from odoo.tools.safe_eval import safe_eval


class WACompose(models.TransientModel):
    _name = 'wa.compose'
    _description = 'WhatsApp Compose Message'

    whatsapp_account_id = fields.Many2one(
        'wa.account',
        string="WhatsApp Account",
        required=True,
        help="Select the WhatsApp account to use for sending the message."
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        help="Select the recipients for the WhatsApp message."
    )
    template_id = fields.Many2one(
        'wa.template',
        string="Template",
        domain="[('model', '=', res_model)]",
        help="Select a WhatsApp template to use for the message."
    )
    message = fields.Text(string="Message", required=True, help="Enter the WhatsApp message.")
    whatsapp_media = fields.Binary(string="Media File", help="Attach a media file to send.")
    whatsapp_media_filename = fields.Char(string="Media Filename", help="Filename of the media file.")
    res_model = fields.Char(string="Related Document Model", help="The model of the related document.")
    model = fields.Char(
        string="Technical Model Name",
        compute='_compute_model',
        readonly=False,
        store=True,
        help="Technical field: model name of the related document (auto-computed)."
    )
    res_id = fields.Integer(string="Related Document ID", help="The ID of the related document.")

    @api.depends('res_model')
    def _compute_model(self):
        """
        Compute the technical model field from res_model or context.
        """
        for wizard in self:
            wizard.model = wizard.res_model or self.env.context.get('default_res_model')


    @api.model
    def default_get(self, fields):
        """
        Set the default WhatsApp account and context for dynamic placeholder rendering.
        """
        res = super(WACompose, self).default_get(fields)
        default_account = self.env['wa.account'].search([('company_id', '=', self.env.company.id)], limit=1)
        if default_account:
            res['whatsapp_account_id'] = default_account.id

        partner_id = self.env.context.get('default_partner_id')
        if not partner_id:
            res_model = self.env.context.get('default_res_model')
            res_id = self.env.context.get('default_res_id')
            if res_model and res_id:
                record = self.env[res_model].browse(res_id)
                if hasattr(record, 'partner_id') and record.partner_id:
                    partner_id = record.partner_id.id
        if partner_id:
            res['partner_ids'] = [(6, 0, [partner_id])]
        return res

    @api.onchange('template_id', 'res_id', 'res_model')
    def _onchange_template_id(self):
        """
        Render the template using the selected record and fill the message field.
        """
        if self.template_id:
            record = None
            if self.res_model and self.res_id:
                record = self.env[self.res_model].browse(self.res_id)
                if not record or not record.exists():
                    record = None
            if record:
                try:
                    message = self.template_id.render_template('message', record)
                    if not isinstance(message, str):
                        message = str(message) if message is not None else ''
                    self.message = message or ''
                    self.whatsapp_media = self.template_id.whatsapp_media
                    self.whatsapp_media_filename = self.template_id.whatsapp_media_filename
                except Exception:
                    self.message = 'error'
                    self.whatsapp_media = self.template_id.whatsapp_media
                    self.whatsapp_media_filename = self.template_id.whatsapp_media_filename
            else:
                self.message = self.template_id.message or ''
                self.whatsapp_media = self.template_id.whatsapp_media
                self.whatsapp_media_filename = self.template_id.whatsapp_media_filename
        else:
            self.message = False
            self.whatsapp_media = False
            self.whatsapp_media_filename = False

    def send_message(self):
        """
        Send the WhatsApp message to the selected recipients.
        """
        if not self.partner_ids:
            raise ValueError(_("Please select at least one recipient."))

        mixin = self.env['wa.mixin']
        for partner in self.partner_ids:
            if not partner.mobile:
                raise ValueError(_("The partner %s does not have a mobile number.") % partner.name)

            mixin.send_whatsapp(
                mobile=partner.mobile,
                message=self.message,
                media=self.whatsapp_media,
                media_filename=self.whatsapp_media_filename,
                res_model=self.res_model,
                res_id=self.res_id,
                whatsapp_account_id=self.whatsapp_account_id.id
            )
