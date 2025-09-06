from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def wa_get_or_create_by_mobile(self, mobile, name=None):
        Partner = self.sudo()
        partner = Partner.search([('mobile', '=', mobile)], limit=1)
        clean_name = (name or '').strip()
        # If provided name equals the mobile (or is empty), treat it as missing
        if clean_name and mobile and clean_name == str(mobile):
            clean_name = ''
        if partner:
            # If partner was previously created with mobile as name or empty/default, update to clean_name
            current = (partner.name or '').strip()
            default_label = _('WhatsApp Contact')
            if clean_name and (not current or current == str(mobile) or current == default_label):
                partner.write({'name': clean_name})
            elif current == str(mobile):
                # No clean_name available but current is mobile: set to default label
                partner.write({'name': default_label})
            return partner
        # Create new partner with a friendly name (prefer clean_name over mobile)
        partner = Partner.create({'name': clean_name or _('WhatsApp Contact'), 'mobile': mobile})
        return partner

    def wa_get_or_create_channel(self, account=None):
        self.ensure_one()
        Channel = self.env['discuss.channel'].sudo()
        domain = [('is_wa', '=', True), ('wa_partner_id', '=', self.id)]
        if account and 'wa_account_id' in Channel._fields:
            domain.append(('wa_account_id', '=', account.id))
        channel = Channel.search(domain, limit=1)
        if channel:
            # If channel exists but has no account set, attach it
            if account and 'wa_account_id' in Channel._fields and not channel.wa_account_id:
                channel.write({'wa_account_id': account.id})
            return channel
        # If an account was provided but an existing channel with a different account exists,
        # do not reuse it; create a dedicated channel for this account.
        vals = {
            'name': self.name,
            'channel_type': 'channel',
            'is_wa': True,
            'wa_partner_id': self.id,
        }
        if account and 'wa_account_id' in Channel._fields:
            vals['wa_account_id'] = account.id
        # seed channel avatar from partner image if available
        if self.image_1920:
            if 'avatar_128' in Channel._fields:
                vals['avatar_128'] = self.image_1920
            if 'image_128' in Channel._fields:
                vals['image_128'] = self.image_1920
        return Channel.create(vals)
