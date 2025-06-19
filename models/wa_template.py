from odoo import _, api, fields, models
import re
import logging

_logger = logging.getLogger(__name__)


class WATemplate(models.Model):
    _name = 'wa.template'
    _description = 'WhatsApp Template'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, tracking=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade', tracking=True)
    model = fields.Char(string='Related Document Model', compute='_compute_model', store=True, readonly=False, tracking=True)
    message = fields.Text(string="Message", help="Message body for WhatsApp (plain text).", tracking=True)
    whatsapp_media = fields.Binary(string="Media File", help="Attach a media file for the template.", tracking=True)
    whatsapp_media_filename = fields.Char(string="Media Filename", help="Filename of the media file.", tracking=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'wa_template_ir_attachments_rel', 'wa_template_id', 'attachment_id',
        string='Attachments'
    )
    lang_id = fields.Many2one(
        'res.lang',
        string='Language',
        help='Language to use for rendering this template. If not set, uses recipient or user language.'
    )

    @api.depends('model_id')
    def _compute_model(self):
        for rec in self:
            rec.model = rec.model_id.model if rec.model_id else False

    def render_template(self, template_field, record):
        """
        Renders the WhatsApp template with the given record and context.

        Allowed template blocks and syntax:
        - Simple variable: {{ field_name }} or {{ object.field_name }}
        - Nested attribute: {{ partner_id.name }}
        - Currency formatting: {{ format_currency(amount_total, currency_id) }}
        - For loop block:
            {% for line in invoice_line_ids %}
                {{ line.name }}: {{ format_currency(line.price_total, line.currency_id) }}
            {% endfor %}
        - Any valid Python expression using fields of the record, e.g. {{ amount_total > 100 }}
        - Access to the current record as 'object' in expressions
        - Access to the context as 'ctx' in expressions

        Example of using context (ctx):
            Suppose you pass ctx={'greeting': 'Hello'} to process_object_blocks, you can use:
                {{ ctx['greeting'] }} {{ partner_id.name }}
            This will render as: Hello John Doe

        Args:
            template_field (str): The field name of the template (e.g., 'message').
            record (recordset): The Odoo record to use for rendering.

        Returns:
            str: The rendered template string.
        """
        self.ensure_one()
        if not record or not record.exists():
            return ''
        template = self[template_field]
        if not template:
            return ''

        # Use template language if set, else recipient/user/default
        lang = self.lang_id.code or getattr(record, 'lang', False) or self.env.user.lang or 'en_US'
        print(lang)
        record = record.with_context(lang=lang)

        def format_currency(amount, currency):
            if not currency:
                return str(amount)
            try:
                formatted = currency.with_context(lang=lang).format(amount)
                _logger.info(f"[WA TEMPLATE] Formatting currency: amount={amount}, currency={currency.name}, lang={lang}, formatted={formatted}")
                return formatted
            except Exception as e:
                _logger.warning(f"[WA TEMPLATE] Currency formatting failed: {e}")
                symbol = getattr(currency, 'symbol', '')
                position = getattr(currency, 'position', 'after')
                try:
                    amount_str = ('%.2f' % float(amount))
                except Exception:
                    amount_str = str(amount)
                if position == 'before':
                    return f"{symbol} {amount_str}"
                else:
                    return f"{amount_str} {symbol}"

        def get_attr(obj, attr_path):
            """Allows access to nested attributes, e.g. partner_id.name"""
            for attr in attr_path.split('.'):
                obj = getattr(obj, attr, '')
                if callable(obj):
                    obj = obj()
                if obj is None:
                    return ''
            return obj if obj is not None else ''

        def replacer(match):
            var_path = match.group(1).strip()
            value = get_attr(record, var_path)
            return str(value) if value is not None else ''

        def process_object_blocks(text, record, ctx=None):
            """
            Supports {{ ... }} for expressions and {% for ... %}{% endfor %} for loops.
            """
            ctx = ctx or {}

            def for_replacer(match):
                loop_code = match.group(1).strip()
                loop_body = match.group(2)
                m = re.match(r'for\s+(\w+)\s+in\s+([^\s]+)', loop_code)
                if not m:
                    return ''
                var_name, list_expr = m.groups()
                local_ctx = {'object': record, 'ctx': ctx, 'format_currency': format_currency}
                if record:
                    for field in record._fields:
                        local_ctx[field] = getattr(record, field, None)
                try:
                    items = eval(list_expr, {}, local_ctx)
                except Exception as e:
                    return f"[error: {e}]"
                result = []
                for item in items:
                    loop_ctx = dict(local_ctx)
                    loop_ctx[var_name] = item
                    def inner_replacer(m2):
                        expr = m2.group(1).strip()
                        try:
                            return str(eval(expr, {}, loop_ctx))
                        except Exception as e:
                            return f"[error: {e}]"
                    result.append(re.sub(r"\{\{\s*(.*?)\s*\}\}", inner_replacer, loop_body))
                return ''.join(result)

            # First process for blocks
            text = re.sub(r"\{%([^%]+)%\}([\s\S]*?)\{% endfor %\}", for_replacer, text)

            # Then process remaining {{ ... }}
            def replacer(match):
                expr = match.group(1).strip()
                local_ctx = {'object': record, 'ctx': ctx, 'format_currency': format_currency}
                if record:
                    for field in record._fields:
                        local_ctx[field] = getattr(record, field, None)
                try:
                    return str(eval(expr, {}, local_ctx))
                except Exception as e:
                    return f"[error: {e}]"
            return re.sub(r"\{\{\s*(.*?)\s*\}\}", replacer, text)

        rendered = process_object_blocks(template, record)
        rendered = re.sub(r'{{\s*([\w\.]+)\s*}}', replacer, rendered)
        return rendered


