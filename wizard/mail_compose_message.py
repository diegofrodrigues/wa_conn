from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools.mail import html2plaintext


class MailComposer(models.TransientModel):
    _name = 'mail.compose.message'
    _inherit = ['mail.composer.mixin', 'mail.compose.message']
    _description = 'Email composition wizard'
    _log_access = True

    send_whatsapp = fields.Boolean()
    whatsapp_account_id = fields.Many2one(
        'whatsapp.account',
        string="WhatsApp Account",
        required=True,
        help="Select the WhatsApp account to use for sending the message."
    )

    @api.model
    def default_get(self, fields):
        """
        Set the default WhatsApp account based on the current company.
        """
        res = super(MailComposer, self).default_get(fields)
        default_account = self.env['whatsapp.account'].search([('company_id', '=', self.env.company.id)], limit=1)
        if default_account:
            res['whatsapp_account_id'] = default_account.id
        return res

    def action_send_mail(self):
        """
        Override the send mail action to send both WhatsApp and email messages if `send_whatsapp` is True.
        """
        if self.send_whatsapp:
            # Validate WhatsApp account
            if not self.whatsapp_account_id:
                raise UserError(_("Invalid WhatsApp account specified."))

            # Fetch the partner's mobile number
            if not self.partner_ids:
                raise UserError(_("No partner is associated with this message."))
            partner = self.partner_ids[0]  # Use the first partner in the list
            if not partner.mobile:
                raise UserError(_("The partner does not have a mobile number."))

            recipient_number = partner.mobile  # Use the partner's mobile number

            # Convert the `body` field (HTML) to plain text
            message_content = html2plaintext(self.body)

            if not message_content:
                raise UserError(_("Message content is empty. Please provide a message."))

            # Fetch res_model and res_id from the context
            res_model = self.env.context.get('active_model')
            res_id = self.env.context.get('active_id')

            if not res_model or not res_id:
                raise UserError(_("No associated record found to log the WhatsApp message."))

            # Use whatsapp.mixin to send the message
            mixin = self.env['whatsapp.mixin']
            if self.attachment_ids:
                for attachment in self.attachment_ids:
                    mixin.send_whatsapp(
                        mobile=recipient_number,
                        message=message_content,
                        media=attachment.datas,
                        media_filename=attachment.name,
                        res_model=res_model,
                        res_id=res_id,
                        whatsapp_account_id=self.whatsapp_account_id.id
                    )
            else:
                mixin.send_whatsapp(
                    mobile=recipient_number,
                    message=message_content,
                    res_model=res_model,
                    res_id=res_id,
                    whatsapp_account_id=self.whatsapp_account_id.id
                )

        # Call the parent method to send the email
        return super().action_send_mail()
