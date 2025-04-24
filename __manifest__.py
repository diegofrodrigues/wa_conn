# -*- coding: utf-8 -*-
{
    'name': 'Bitconn Technology',
    'summary': '''
        Integration for whatsapp with qrcode API.''',

    'description': '''
        This is a module for integrate whatsapp and send messages
        with develop API. This module is developed by Bitconn Technology.
        This module is not official and is not supported by Odoo.''',

    'author':'Diego Ferreira',
    'website': 'https://bitconn.com.br',
    'version': '1.0.0',
    'category': 'tools',
    'description': 'Bitconn Integration',
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'depends': ['base','mail','sale','account', 'base_automation'],
    'data': [
        'security/ir.model.access.csv',
        'views/ir_actions_server_views.xml',
        'views/whatsapp_account_views.xml',
        'views/whatsapp_message_views.xml',
        'views/whatsapp_compose_views.xml',
        'wizard/mail_compose_message_wizard.xml',
        'wizard/account_move_send_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
        ],
    },
}