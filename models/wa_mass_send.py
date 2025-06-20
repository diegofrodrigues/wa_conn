import time
import random
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class WAMassSend(models.Model):
    _name = 'wa.mass.send'
    _description = 'Mass WhatsApp Sender'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, tracking=True)
    whatsapp_account_id = fields.Many2one(
        'wa.account',
        string="WhatsApp Account",
        required=True,
        help="WhatsApp account to use.",
        tracking=True
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        required=True,
        help="Recipients to send WhatsApp messages to.",
        tracking=True,
        ondelete='cascade'
    )
    template_id = fields.Many2one(
        'wa.template',
        string="Template",
        domain="[('model', '=', 'res.partner')]",
        help="WhatsApp template to use.",
        tracking=True
    )
    message = fields.Text(string="Message", help="Message to send.", tracking=True)
    min_delay = fields.Integer(string="Min Delay (seconds)", default=2, required=True, tracking=True)
    max_delay = fields.Integer(string="Max Delay (seconds)", default=10, required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], default='draft', string="Status", tracking=True)
    last_send_date = fields.Datetime(string="Last Send Date", tracking=True)
    error_message = fields.Text(string="Error Message", tracking=True)
    scheduled_datetime = fields.Datetime(string="Scheduled Date/Time", required=True, help="When to start sending messages (for cron).", tracking=True)
    cron_enabled = fields.Boolean(string="Enable Scheduled Send", default=False, help="If enabled, this record will be processed by the cron job.", tracking=True)

    cron_interval_number = fields.Integer(
        string="Cron Interval Number",
        default=1,
        help="Interval number between cron executions."
    )
    cron_interval_type = fields.Selection(
        [
            ('minutes', 'Minutes'),
            ('hours', 'Hours'),
            ('days', 'Days'),
            ('weeks', 'Weeks'),
            ('months', 'Months')
        ],
        required=True,
        string="Cron Interval Type",
        default='minutes',
        help="Type of interval between cron executions."
    )

    def get_cron_for_mass_send(self):
        """
        Search and return the cron related to this wa.mass.send record.
        """
        IrCron = self.env['ir.cron'].sudo()
        model_ref = self.env['ir.model']._get_id('wa.mass.send')
        cron_code = f"model.browse({self.id}).action_send()"
        crons = IrCron.with_context(active_test=False).search([
            ('model_id', '=', model_ref),
            ('code', '=', cron_code),
        ])
        # Remove duplicates, if any, and notify the user
        if len(crons) > 1:
            crons[1:].unlink()
            raise UserError(_('There were duplicate crons for this mass send. Duplicates were removed and only one was kept.'))
        return crons[0] if crons else False

    def _update_cron(self):
        """
        Activate or deactivate the ir.cron job according to cron_enabled.
        Always reuse the existing cron, even if deactivated. Never create duplicates.
        """
        cron = self.get_cron_for_mass_send()
        if cron and cron.active:
            try:
                with self.env.cr.savepoint():
                    self.env.cr.execute(f"SELECT 1 FROM ir_cron WHERE id=%s FOR UPDATE NOWAIT", (cron.id,))
            except Exception as e:
                raise UserError(_(
                    'It was not possible to change or deactivate the schedule because it is currently being processed (automatic or manual execution).\n'
                    'Please wait for the current execution to finish and try again.\n'
                    'If the problem persists, refresh the page and check if the mass send has already been completed.'
                ))
        cron_name = f"WA Mass Send: {self.name}-{self.id}"
        cron_code = f"model.browse({self.id}).action_send()"
        if self.cron_enabled:
            if cron:
                cron.write({
                    'name': cron_name,
                    'active': True,
                    'nextcall': self.scheduled_datetime or fields.Datetime.now(),
                    'interval_number': self.cron_interval_number or 1,
                    'interval_type': self.cron_interval_type or 'minutes',
                })
            else:
                self.env['ir.cron'].sudo().create({
                    'name': cron_name,
                    'model_id': self.env['ir.model']._get_id('wa.mass.send'),
                    'state': 'code',
                    'code': cron_code,
                    'user_id': self.env.user.id,
                    'active': True,
                    'interval_number': self.cron_interval_number or 1,
                    'interval_type': self.cron_interval_type or 'minutes',
                    'nextcall': self.scheduled_datetime or fields.Datetime.now(),
                })
        elif cron:
            try:
                with self.env.cr.savepoint():
                    self.env.cr.execute(f"SELECT 1 FROM ir_cron WHERE id=%s FOR UPDATE NOWAIT", (cron.id,))
            except Exception:
                raise UserError(_('It is not possible to deactivate the schedule while the cron is running. Please wait for the execution to finish before deactivating.'))
            cron.write({'active': False})

    @api.model_create_multi
    def create(self, vals_list):
        """
        Create records and schedule the cron if necessary.
        """
        records = super().create(vals_list)
        return records

    def write(self, vals):
        res = super().write(vals)
        self._update_cron()
        return res

    def action_send(self):
        self.write({'state': 'sending'})
        self._send_mass_message_backend()

    def _send_mass_message_backend(self):
        mixin = self.env['wa.mixin']
        try:
            for partner in self.partner_ids:
                if not partner.mobile:
                    continue
                msg = self.message
                if self.template_id:
                    msg = self.template_id.render_template('message', partner)
                mixin.send_whatsapp(
                    mobile=partner.mobile,
                    message=msg,
                    media=self.template_id.whatsapp_media if self.template_id else False,
                    media_filename=self.template_id.whatsapp_media_filename if self.template_id else False,
                    whatsapp_account_id=self.whatsapp_account_id.id
                )
                delay = random.uniform(self.min_delay, self.max_delay)
                time.sleep(delay)
            self.write({'state': 'done', 'last_send_date': fields.Datetime.now(), 'error_message': False})
        except Exception as e:
            self.write({'state': 'error', 'error_message': str(e)})

    @api.model
    def cron_send_mass_messages(self):
        """
        Method to be called by a scheduled action (ir.cron) to process scheduled mass sends.
        Now runs every time it is scheduled, with no execution limit per record.
        """
        now = fields.Datetime.now()
        mass_sends = self.search([
            ('state', '=', 'scheduled'),
            ('cron_enabled', '=', True),
            '|',
            ('scheduled_datetime', '=', False),
            ('scheduled_datetime', '<=', now),
        ])
        for mass_send in mass_sends.sudo():
            mass_send.action_send()
