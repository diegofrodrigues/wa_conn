# -*- coding: utf-8 -*-
{
    'name': 'Wa Conn',
    'summary': '''
        Integration for wa with qrcode API.''',

    'description': '''
        This is a module for integrate wa and send messages
        with develop API. This module is developed by Bitconn Technology.
        This module is not official and is not supported by Odoo.''',

    'author':'Diego Ferreira',
    'website': 'https://bitconn.com.br',
    'version': '1.0.0',
    'category': 'tools',
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'depends': ['base','mail','sale','account', 'base_automation'],
    'data': [
        'security/ir.model.access.csv',
        'views/ir_actions_server_views.xml',
        'views/wa_account_views.xml',
        'views/wa_message_views.xml',
        'views/wa_compose_views.xml',
        'wizard/mail_compose_message.xml',
        'wizard/account_move_send.xml',
    ],
    'assets': {
        'web.assets_backend': [
        ],
    },
}