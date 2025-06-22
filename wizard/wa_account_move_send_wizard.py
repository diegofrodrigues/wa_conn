from odoo import _, models, fields, api
from odoo.exceptions import UserError
from odoo.tools import html2plaintext
import json


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    whatsapp_account_id = fields.Many2one(
        'wa.account',
        string="WhatsApp Account",
        required=False,
        help="Select the WhatsApp account to use for sending the message."
    )

    @api.model
    def default_get(self, fields):
        """
        Set the default WhatsApp account based on the current company.
        """
        res = super(AccountMoveSendWizard, self).default_get(fields)
        default_account = self.env['wa.account'].search([('company_id', '=', self.env.company.id)], limit=1)
        if default_account:
            res['whatsapp_account_id'] = default_account.id
        return res
    
    @api.model
    def _hook_if_success(self, moves_data):
        """ Process (typically send) successful documents."""
        sending_methods = self.sending_method_checkboxes or {}
        print(sending_methods)
        if len(sending_methods) == 1 and sending_methods.get('whatsapp', {}).get('checked'):
            return
        else:
            to_send_mail = {
                move: move_data
                for move, move_data in moves_data.items()
                if 'email' in move_data['sending_methods'] and self._is_applicable_to_move('email', move)
            }
            self._send_mails(to_send_mail)
    
    @api.depends('move_id')
    def _compute_sending_method_checkboxes(self):
        super()._compute_sending_method_checkboxes()
        methods = self.env['ir.model.fields'].get_field_selection('res.partner', 'invoice_sending_method')
        for wizard in self:
            preferred_method = self._get_default_sending_method(wizard.move_id)
            need_fallback = not self._is_applicable_to_move(preferred_method, wizard.move_id)
            fallback_method = need_fallback and ('email' if self._is_applicable_to_move('email', wizard.move_id) else 'manual')
            checkboxes = {
                method_key: {
                    'checked': method_key == preferred_method if not need_fallback else method_key == fallback_method,
                    'label': method_label,
                }
                for method_key, method_label in methods if self._is_applicable_to_company(method_key, wizard.company_id)
            }
            checkboxes['whatsapp'] = {
                'checked': False,
                'label': 'WhatsApp',
            }
            wizard.sending_method_checkboxes = checkboxes

    def action_send_only_whatsapp(self):
        """
        Override the send mail action to send WhatsApp messages using WhatsAppMixin.
        """
        sending_methods = self.sending_method_checkboxes or {}
        if sending_methods.get('whatsapp', {}).get('checked'):

            # Validate WhatsApp account
            if not self.whatsapp_account_id:
                raise UserError(_("Please select a valid WhatsApp account."))

            # Fetch the partner's mobile number
            if not self.mail_partner_ids:
                raise UserError(_("No partner is associated with this message."))
            partner = self.mail_partner_ids[0]  # Use the first partner in the list
            if not partner.mobile:
                raise UserError(_("The partner does not have a mobile number."))

            recipient_number = partner.mobile  # Use the partner's mobile number

            # Convert the `mail_body` field (HTML) to plain text
            message_content = html2plaintext(self.mail_body)

            if not message_content:
                raise UserError(_("Message content is empty. Please provide a message."))
            # Use WhatsAppMixin to send the message
            mixin = self.env['wa.mixin']
            if self.mail_attachments_widget:
                # Filter valid attachment IDs
                attachment_ids = [
                    attachment['id'] for attachment in self.mail_attachments_widget
                    if isinstance(attachment['id'], int)]
                
                # Fetch the attachment records
                attachments = self.env['ir.attachment'].browse(attachment_ids)
                if not attachment_ids:
                    attachments = self._generate_and_send_invoices(
                        self.move_id,
                    )

                for attachment in attachments:
                    mixin.send_whatsapp(
                        mobile=recipient_number,
                        message=message_content,
                        media=attachment.datas,
                        media_filename=attachment.name,
                        res_model='account.move',
                        res_id=self.move_id.id,
                        whatsapp_account_id=self.whatsapp_account_id.id
                    )
            else:
                mixin.send_whatsapp(
                    mobile=recipient_number,
                    message=message_content,
                    res_model='account.move',
                    res_id=self.move_id.id,
                    whatsapp_account_id=self.whatsapp_account_id.id
                )

    def action_send_and_print(self):
        sending_methods = self.sending_method_checkboxes or {}
        selected_methods = [method for method, vals in sending_methods.items() if vals.get('checked')]
        if len(selected_methods) > 1 and 'whatsapp' in selected_methods: #TODO: fix sending mail and whats after you have attachment
            self.action_send_only_whatsapp()
        elif selected_methods == ['email']:
            return super(AccountMoveSendWizard, self).action_send_and_print()
        elif selected_methods == ['whatsapp']:
            self.action_send_only_whatsapp()
        else:
            return super(AccountMoveSendWizard, self).action_send_and_print()
