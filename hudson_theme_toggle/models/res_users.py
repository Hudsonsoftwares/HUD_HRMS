# -*- coding: utf-8 -*-
from odoo import fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    dark_mode = fields.Boolean(
        string='Dark Mode',
        default=False,
        help='User preference for Odoo backend dark mode theme'
    )
