# -*- coding: utf-8 -*-
from datetime import datetime, time
from odoo import api, fields, models, _


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_discrepancy_hours = fields.Float(
        string='Attendance Discrepancy Hours',
        compute='_compute_attendance_discrepancy',
        search='_search_attendance_discrepancy_hours',
        store=False,
    )
    has_attendance_discrepancy = fields.Boolean(
        string='Has Attendance Discrepancy',
        compute='_compute_attendance_discrepancy',
        search='_search_has_attendance_discrepancy',
        store=False,
    )
    attendance_discrepancy_string = fields.Char(
        string='Attendance Mismatch String',
        compute='_compute_attendance_discrepancy_string',
    )

    @api.depends('worked_days_line_ids.number_of_hours', 'worked_days_line_ids.code',
                 'employee_id', 'date_from', 'date_to')
    def _compute_attendance_discrepancy(self):
        for payslip in self:
            if not (payslip.contract_id and payslip.date_from and payslip.date_to):
                payslip.attendance_discrepancy_hours = 0.0
                payslip.has_attendance_discrepancy = False
                continue
            data = payslip._get_attendance_vs_schedule(
                payslip.contract_id, payslip.date_from, payslip.date_to
            )
            discrepancy = data['overtime_hours_delta'] - data['shortage_hours_delta']
            payslip.attendance_discrepancy_hours = discrepancy
            payslip.has_attendance_discrepancy = abs(discrepancy) > 0.01

    def _search_has_attendance_discrepancy(self, operator, value):
        positive = (operator in ('=', '!=') and bool(value) == (operator == '='))
        payslips = self.search([('contract_id', '!=', False), ('date_from', '!=', False), ('date_to', '!=', False)])
        matched_ids = []
        for payslip in payslips:
            data = payslip._get_attendance_vs_schedule(payslip.contract_id, payslip.date_from, payslip.date_to)
            discrepancy = data['overtime_hours_delta'] - data['shortage_hours_delta']
            has_disc = abs(discrepancy) > 0.01
            if has_disc if positive else not has_disc:
                matched_ids.append(payslip.id)
        return [('id', 'in', matched_ids)]

    def _search_attendance_discrepancy_hours(self, operator, value):
        payslips = self.search([('contract_id', '!=', False), ('date_from', '!=', False), ('date_to', '!=', False)])
        matched_ids = []
        for payslip in payslips:
            data = payslip._get_attendance_vs_schedule(payslip.contract_id, payslip.date_from, payslip.date_to)
            discrepancy = data['overtime_hours_delta'] - data['shortage_hours_delta']
            if operator == '=' and abs(discrepancy - value) < 0.01:
                matched_ids.append(payslip.id)
            elif operator == '!=' and abs(discrepancy - value) >= 0.01:
                matched_ids.append(payslip.id)
            elif operator == '>' and discrepancy > value:
                matched_ids.append(payslip.id)
            elif operator == '>=' and discrepancy >= value:
                matched_ids.append(payslip.id)
            elif operator == '<' and discrepancy < value:
                matched_ids.append(payslip.id)
            elif operator == '<=' and discrepancy <= value:
                matched_ids.append(payslip.id)
        return [('id', 'in', matched_ids)]

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
        return res

    def action_compute_sheet(self):
        if hasattr(self.env, '_attendance_cache'):
            self.env._attendance_cache.clear()
        return super(HrPayslip, self).action_compute_sheet()

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
