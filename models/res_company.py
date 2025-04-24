from odoo import _, models, fields
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = 'res.company'

    base_url = fields.Char(string='Base URL',)
    api_key = fields.Char(string='API Key',)
    instance_name = fields.Char(string='Instance Name',)
    # whatsapp_account_ids = fields.Many2many(
    #     'whatsapp.account',
    #     'whatsapp_account_company_rel',
    #     'company_id',
    #     'account_id',
    #     string="WhatsApp Accounts"
    # )  # Reverse many-to-many relationship
