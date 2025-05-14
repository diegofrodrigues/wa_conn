from odoo import _, models, fields
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = 'res.company'

    base_url = fields.Char(string='Base URL',)
    api_key = fields.Char(string='API Key',)
    instance_name = fields.Char(string='Instance Name',)

