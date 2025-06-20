from . import models
from . import controllers
from . import wizard


def uninstall_hook(env):
    actions = env['ir.actions.server'].search([
        '|',
        ('model_id.model', '=', 'wa.account'),
        ('model_id.model', '=', 'wa.template'),
    ])
    actions.unlink()
    views = env['ir.ui.view'].search([('name', 'ilike', 'wa.conn')])
    for view in views:
        view.unlink()
    menu_ids = []
    menus = env['ir.ui.menu'].search([
        '|',
        ('action', 'like', 'ir.actions.server,%'),
        ('action', 'like', 'ir.actions.act_window,%'),
    ])
    for menu in menus:
        xmlid = env['ir.model.data'].search([
            ('model', '=', 'ir.ui.menu'),
            ('res_id', '=', menu.id),
            ('module', '=', 'wa_conn')
        ], limit=1)
        if xmlid:
            menu_ids.append(menu.id)
    env['ir.ui.menu'].browse(menu_ids).unlink()
    datas = env['ir.model.data'].search([('module', '=', 'wa_conn')])
    datas.unlink()