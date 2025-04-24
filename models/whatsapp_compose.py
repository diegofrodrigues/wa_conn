from odoo import _, api, fields, models


class WhatsAppCompose(models.TransientModel):
    _name = 'whatsapp.compose'
    _description = 'WhatsApp Compose Message'

    whatsapp_account_id = fields.Many2one(
        'whatsapp.account',
        string="WhatsApp Account",
        required=True,
        help="Select the WhatsApp account to use for sending the message."
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        help="Select the recipients for the WhatsApp message."
    )
    message = fields.Text(string="Message", required=True, help="Enter the WhatsApp message.")
    whatsapp_media = fields.Binary(string="Media File", help="Attach a media file to send.")
    whatsapp_media_filename = fields.Char(string="Media Filename", help="Filename of the media file.")
    res_model = fields.Char(string="Related Document Model", help="The model of the related document.")
    res_id = fields.Integer(string="Related Document ID", help="The ID of the related document.")

    @api.model
    def default_get(self, fields):
        """
        Set the default WhatsApp account based on the current company.
        """
        res = super(WhatsAppCompose, self).default_get(fields)
        default_account = self.env['whatsapp.account'].search([('company_id', '=', self.env.company.id)], limit=1)
        if default_account:
            res['whatsapp_account_id'] = default_account.id
        return res

    def send_message(self):
        """
        Send the WhatsApp message to the selected recipients.
        """
        if not self.partner_ids:
            raise ValueError(_("Please select at least one recipient."))

        mixin = self.env['whatsapp.mixin']
        for partner in self.partner_ids:
            if not partner.mobile:
                raise ValueError(_("The partner %s does not have a mobile number.") % partner.name)

            mixin.send_whatsapp(
                mobile=partner.mobile,
                message=self.message,
                media=self.whatsapp_media,
                media_filename=self.whatsapp_media_filename,
                res_model=self.res_model,  # Use res_model
                res_id=self.res_id,        # Use res_id
                whatsapp_account_id=self.whatsapp_account_id.id
            )
