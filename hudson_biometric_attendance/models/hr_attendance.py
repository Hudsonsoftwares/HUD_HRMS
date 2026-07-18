# -*- coding: utf-8 -*-
from odoo import models

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    def _validate_check_in_location(self, vals):
        # Bypass browser location validation for automated biometric/API punches
        if self.env.context.get('biometric_punch_processing'):
            return
        if hasattr(super(), '_validate_check_in_location'):
            super()._validate_check_in_location(vals)

    def _validate_check_out_location(self, vals):
        # Bypass browser location validation for automated biometric/API punches
        if self.env.context.get('biometric_punch_processing'):
            return
        if hasattr(super(), '_validate_check_out_location'):
            super()._validate_check_out_location(vals)
