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
    message = fields.Html(string="Message", required=True, help="Enter the WhatsApp message.")
    whatsapp_media = fields.Binary(string="Media File", help="Attach a media file to send.")
    whatsapp_media_filename = fields.Char(string="Media Filename", help="Filename of the media file.")
    res_model = fields.Char(string="Related Document Model", help="The model of the related document.")
    res_id = fields.Integer(string="Related Document ID", help="The ID of the related document.")

    @api.onchange('template_id', 'res_id', 'res_model')
    def _onchange_template_id(self):
        """
        Render the template using the selected record, similar to mail.compose.message.
        """
        if self.template_id and self.res_model and self.res_id:
            record = self.env[self.res_model].browse(self.res_id)
            try:
                values = self.template_id.generate_whatsapp_values(record)
                self.message = values['message']
                self.whatsapp_media = values['whatsapp_media']
                self.whatsapp_media_filename = values['whatsapp_media_filename']
            except Exception:
                self.message = self.template_id.message
                self.whatsapp_media = self.template_id.whatsapp_media
                self.whatsapp_media_filename = self.template_id.whatsapp_media_filename
        elif self.template_id:
            # If no record, just copy the template message as is
            self.message = self.template_id.message
            self.whatsapp_media = self.template_id.whatsapp_media
            self.whatsapp_media_filename = self.template_id.whatsapp_media_filename

    @api.model
    def default_get(self, fields):
        """
        Set the default WhatsApp account and context for dynamic placeholder rendering.
        """
        res = super(WACompose, self).default_get(fields)
        default_account = self.env['wa.account'].search([('company_id', '=', self.env.company.id)], limit=1)
        if default_account:
            res['whatsapp_account_id'] = default_account.id

        # Set default partner if context provides it
        partner_id = self.env.context.get('default_partner_id')
        if not partner_id:
            # Try to get from res_model/res_id if possible
            res_model = self.env.context.get('default_res_model')
            res_id = self.env.context.get('default_res_id')
            if res_model and res_id:
                record = self.env[res_model].browse(res_id)
                if hasattr(record, 'partner_id') and record.partner_id:
                    partner_id = record.partner_id.id
        if partner_id:
            res['partner_ids'] = [(6, 0, [partner_id])]
        return res

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
