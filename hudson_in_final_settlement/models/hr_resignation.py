# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrResignation(models.Model):
    _inherit = 'hr.resignation'

    final_settlement_ids = fields.One2many(
        'final.settlement',
        'resignation_id',
        string="Final Settlements"
    )
    final_settlement_count = fields.Integer(
        string="Final Settlement Count",
        compute='_compute_final_settlement_count'
    )

    @api.depends('final_settlement_ids', 'final_settlement_ids.state')
    def _compute_final_settlement_count(self):
        for record in self:
            record.final_settlement_count = len(record.final_settlement_ids.filtered(lambda s: s.state != 'cancel'))

    def action_create_final_settlement(self):
        """
        Creates a Final Settlement master record from an approved resignation.
        Prevents duplicate active settlement creation.
        """
        self.ensure_one()
        if self.state not in ('approved', 'confirm'):
            raise UserError(_("Final Settlement can only be created for approved or confirmed resignation requests."))

        # Check for existing active settlement
        existing = self.env['final.settlement'].search([
            ('resignation_id', '=', self.id),
            ('state', '!=', 'cancel')
        ], limit=1)

        if existing:
            return {
                'name': _('Final Settlement'),
                'type': 'ir.actions.act_window',
                'res_model': 'final.settlement',
                'res_id': existing.id,
                'view_mode': 'form',
                'target': 'current',
            }

        last_day = self.approved_revealing_date or self.expected_revealing_date or fields.Date.today()
        company = self.employee_id.company_id or self.env.company

        settlement = self.env['final.settlement'].create({
            'employee_id': self.employee_id.id,
            'company_id': company.id,
            'resignation_id': self.id,
            'last_working_day': last_day,
            'settlement_date': fields.Date.today(),
            'exit_reason': 'resignation',
            'state': 'draft',
        })

        return {
            'name': _('Final Settlement'),
            'type': 'ir.actions.act_window',
            'res_model': 'final.settlement',
            'res_id': settlement.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_final_settlement(self):
        """Action for smart button to view linked final settlement."""
        self.ensure_one()
        settlements = self.final_settlement_ids.filtered(lambda s: s.state != 'cancel')
        if not settlements:
            return self.action_create_final_settlement()

        if len(settlements) == 1:
            return {
                'name': _('Final Settlement'),
                'type': 'ir.actions.act_window',
                'res_model': 'final.settlement',
                'res_id': settlements[0].id,
                'view_mode': 'form',
                'target': 'current',
            }

        return {
            'name': _('Final Settlements'),
            'type': 'ir.actions.act_window',
            'res_model': 'final.settlement',
            'domain': [('resignation_id', '=', self.id), ('state', '!=', 'cancel')],
            'view_mode': 'list,form',
            'target': 'current',
        }
