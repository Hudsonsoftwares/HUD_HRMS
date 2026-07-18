# -*- coding: utf-8 -*-
from odoo import fields, models

class HrVersion(models.Model):
    _inherit = 'hr.version'

    overtime_rate_per_hour = fields.Float(
        string='Overtime Rate (per hour)',
        default=0.0,
    )
    shortage_deduction_rate_per_hour = fields.Float(
        string='Shortage Deduction Rate (per hour)',
        default=0.0,
    )
