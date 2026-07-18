# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request

class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        # Guard for unittest context where HTTP request is not bound
        try:
            if not request or not getattr(request, 'session', None):
                return {'hudson_dark_mode': self.env.user.dark_mode}
        except RuntimeError:
            return {'hudson_dark_mode': self.env.user.dark_mode}

        result = super(Http, self).session_info()
        result['hudson_dark_mode'] = self.env.user.dark_mode
        return result
