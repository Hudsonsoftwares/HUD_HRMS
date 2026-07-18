# -*- coding: utf-8 -*-
from odoo import fields, models

class HudsonAttendanceDevice(models.Model):
    _name = 'hudson.attendance.device'
    _description = 'Biometric/Attendance Device Connection'
    _order = 'name'

    name = fields.Char(
        string='Device Name',
        required=True,
        help='A descriptive name for the biometric device or source.'
    )
    connection_type = fields.Selection([
        ('zk_direct', 'ZK Direct Connection'),
        ('rest_api', 'REST API Poll'),
        ('webhook', 'Webhook Push')
    ], string='Connection Type', required=True, default='zk_direct')
    
    address = fields.Char(
        string='Device Address/IP/URL',
        help='The IP address, URL, or API endpoint identifier for this device.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help='Company associated with this attendance device.'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, it will allow you to hide the device without removing it.'
    )
