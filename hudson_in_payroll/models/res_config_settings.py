# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hds_in_epf_applicable = fields.Boolean(
        related='company_id.hds_in_epf_applicable',
        readonly=False,
        string="EPF Applicable"
    )
    hds_in_epf_employer_id = fields.Char(
        related='company_id.hds_in_epf_employer_id',
        readonly=False,
        string="EPF Employer ID"
    )
    hds_in_eps_applicable = fields.Boolean(
        related='company_id.hds_in_eps_applicable',
        readonly=False,
        string="EPS Applicable"
    )
    hds_in_edli_applicable = fields.Boolean(
        related='company_id.hds_in_edli_applicable',
        readonly=False,
        string="EDLI Applicable"
    )
    hds_in_edli_registration_number = fields.Char(
        related='company_id.hds_in_edli_registration_number',
        readonly=False,
        string="EDLI Registration Number"
    )

    hds_in_is_india_company = fields.Boolean(
        string="Is India Company",
        compute='_compute_hds_in_is_india_company'
    )

    @api.depends('company_id', 'company_id.country_id')
    def _compute_hds_in_is_india_company(self):
        for record in self:
            country = record.company_id.country_id
            record.hds_in_is_india_company = bool(
                country and country.code == 'IN'
            )
