# -*- coding: utf-8 -*-
from datetime import datetime, time
from odoo import api, fields, models, _

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_discrepancy_hours = fields.Float(
        string='Attendance Discrepancy Hours',
        store=True,
    )
    has_attendance_discrepancy = fields.Boolean(
        string='Has Attendance Discrepancy',
        store=True,
    )
    attendance_discrepancy_string = fields.Char(
        string='Attendance Mismatch String',
        compute='_compute_attendance_discrepancy_string',
    )

    @api.depends('attendance_discrepancy_hours')
    def _compute_attendance_discrepancy_string(self):
        for payslip in self:
            val = payslip.attendance_discrepancy_hours
            sign = "+" if val >= 0 else ""
            payslip.attendance_discrepancy_string = f"{sign}{val:.1f} hrs"

    def _get_attendance_vs_schedule(self, contract, date_from, date_to):
        """
        Returns a dict: {
            'scheduled_hours': float,
            'actual_hours': float,
            'validated_overtime_hours': float,
            'overtime_hours_delta': float,   # validated OT, >= 0
            'shortage_hours_delta': float,   # scheduled - actual, >= 0 only if positive, else 0
        }
        """
        if not hasattr(self.env, '_attendance_cache'):
            self.env._attendance_cache = {}
        cache_key = (contract.id, date_from, date_to)
        if cache_key in self.env._attendance_cache:
            return self.env._attendance_cache[cache_key]

        super_res = super(HrPayslip, self).get_worked_day_lines(contract, date_from, date_to)
        scheduled_hours = sum(line.get('number_of_hours', 0.0) for line in super_res if line.get('code') == 'WORK100')

        day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
        day_to = datetime.combine(fields.Date.from_string(date_to), time.max)
        
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', contract.employee_id.id),
            ('check_in', '>=', day_from),
            ('check_in', '<=', day_to),
        ])
        actual_hours = sum(attendances.mapped('worked_hours'))
        
        approved_attendances = attendances.filtered(lambda a: a.overtime_status == 'approved')
        validated_overtime_hours = sum(approved_attendances.mapped('validated_overtime_hours'))
        
        overtime_hours_delta = validated_overtime_hours
        shortage_hours_delta = max(scheduled_hours - actual_hours, 0.0)
        
        data = {
            'scheduled_hours': scheduled_hours,
            'actual_hours': actual_hours,
            'validated_overtime_hours': validated_overtime_hours,
            'overtime_hours_delta': overtime_hours_delta,
            'shortage_hours_delta': shortage_hours_delta,
        }
        self.env._attendance_cache[cache_key] = data
        return data

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        res = super(HrPayslip, self).get_worked_day_lines(contracts, date_from, date_to)
        for contract in contracts:
            data = self._get_attendance_vs_schedule(contract, date_from, date_to)
            if data['overtime_hours_delta'] > 0.01:
                res.append({
                    'name': _('Overtime Hours'),
                    'sequence': 5,
                    'code': 'OVERTIME',
                    'number_of_days': 0.0,
                    'number_of_hours': data['overtime_hours_delta'],
                    'contract_id': contract.id,
                })
            if data['shortage_hours_delta'] > 0.01:
                res.append({
                    'name': _('Attendance Shortage'),
                    'sequence': 5,
                    'code': 'SHORTAGE',
                    'number_of_days': 0.0,
                    'number_of_hours': data['shortage_hours_delta'],
                    'contract_id': contract.id,
                })
            
            if self:
                for payslip in self:
                    discrepancy = data['overtime_hours_delta'] - data['shortage_hours_delta']
                    payslip.attendance_discrepancy_hours = discrepancy
                    payslip.has_attendance_discrepancy = abs(discrepancy) > 0.01
        return res

    def action_compute_sheet(self):
        res = super(HrPayslip, self).action_compute_sheet()
        for payslip in self:
            contract = payslip.contract_id
            if contract and payslip.date_from and payslip.date_to:
                data = payslip._get_attendance_vs_schedule(contract, payslip.date_from, payslip.date_to)
                discrepancy = data['overtime_hours_delta'] - data['shortage_hours_delta']
                payslip.write({
                    'attendance_discrepancy_hours': discrepancy,
                    'has_attendance_discrepancy': abs(discrepancy) > 0.01,
                })
        return res

    def action_view_attendance_discrepancy(self):
        self.ensure_one()
        day_from = datetime.combine(fields.Date.from_string(self.date_from), time.min)
        day_to = datetime.combine(fields.Date.from_string(self.date_to), time.max)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attendances'),
            'res_model': 'hr.attendance',
            'view_mode': 'list,form',
            'domain': [
                ('employee_id', '=', self.employee_id.id),
                ('check_in', '>=', day_from),
                ('check_in', '<=', day_to),
            ],
            'context': {
                'default_employee_id': self.employee_id.id,
            },
            'target': 'current',
        }
