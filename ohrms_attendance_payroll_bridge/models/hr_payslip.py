# -*- coding: utf-8 -*-
from datetime import datetime, time
from odoo import api, fields, models, _

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_discrepancy_hours = fields.Float(
        string='Attendance Discrepancy Hours',
        compute='_compute_attendance_discrepancy',
        store=True,
    )
    has_attendance_discrepancy = fields.Boolean(
        string='Has Attendance Discrepancy',
        compute='_compute_attendance_discrepancy',
        store=True,
    )
    attendance_discrepancy_string = fields.Char(
        string='Attendance Mismatch String',
        compute='_compute_attendance_discrepancy_string',
    )

    @api.depends('worked_days_line_ids.number_of_hours', 'worked_days_line_ids.code', 'employee_id', 'date_from', 'date_to')
    def _compute_attendance_discrepancy(self):
        for payslip in self:
            work100_hours = sum(payslip.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100').mapped('number_of_hours'))
            if payslip.employee_id and payslip.date_from and payslip.date_to:
                day_from = datetime.combine(fields.Date.from_string(payslip.date_from), time.min)
                day_to = datetime.combine(fields.Date.from_string(payslip.date_to), time.max)
                attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('check_in', '>=', day_from),
                    ('check_in', '<=', day_to),
                ])
                attendance_hours = sum(attendances.mapped('worked_hours'))
                payslip.attendance_discrepancy_hours = attendance_hours - work100_hours
            else:
                payslip.attendance_discrepancy_hours = -work100_hours
            payslip.has_attendance_discrepancy = abs(payslip.attendance_discrepancy_hours) > 0.01

    @api.depends('attendance_discrepancy_hours')
    def _compute_attendance_discrepancy_string(self):
        for payslip in self:
            val = payslip.attendance_discrepancy_hours
            sign = "+" if val >= 0 else ""
            payslip.attendance_discrepancy_string = f"{sign}{val:.1f} hrs"

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        res = super(HrPayslip, self).get_worked_day_lines(contracts, date_from, date_to)
        
        # Calculate the WORK100 hours from the returned lines
        work100_hours = sum(line.get('number_of_hours', 0.0) for line in res if line.get('code') == 'WORK100')
        
        emp = contracts.employee_id[:1]
        if emp and date_from and date_to:
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', day_from),
                ('check_in', '<=', day_to),
            ])
            attendance_hours = sum(attendances.mapped('worked_hours'))
            
            discrepancy = attendance_hours - work100_hours
            
            # Compute Overtime or Shortage
            overtime_hours = max(0.0, discrepancy)
            shortage_hours = max(0.0, -discrepancy)
            
            # Add OVERTIME worked days line
            if overtime_hours > 0.01:
                res.append({
                    'name': _('Overtime (Attendance)'),
                    'sequence': 10,
                    'code': 'OVERTIME',
                    'number_of_days': overtime_hours / 8.0,
                    'number_of_hours': overtime_hours,
                    'contract_id': contracts[:1].id,
                })
                
            # Add SHORTAGE worked days line
            if shortage_hours > 0.01:
                res.append({
                    'name': _('Shortage (Attendance)'),
                    'sequence': 11,
                    'code': 'SHORTAGE',
                    'number_of_days': shortage_hours / 8.0,
                    'number_of_hours': shortage_hours,
                    'contract_id': contracts[:1].id,
                })
        
        if self:
            for payslip in self:
                p_work100 = sum(line.get('number_of_hours', 0.0) for line in res if line.get('code') == 'WORK100')
                p_emp = payslip.employee_id or contracts.employee_id[:1]
                p_df = payslip.date_from or date_from
                p_dt = payslip.date_to or date_to
                if p_emp and p_df and p_dt:
                    p_day_from = datetime.combine(fields.Date.from_string(p_df), time.min)
                    p_day_to = datetime.combine(fields.Date.from_string(p_dt), time.max)
                    p_attendances = self.env['hr.attendance'].search([
                        ('employee_id', '=', p_emp.id),
                        ('check_in', '>=', p_day_from),
                        ('check_in', '<=', p_day_to),
                    ])
                    p_attendance_hours = sum(p_attendances.mapped('worked_hours'))
                    payslip.attendance_discrepancy_hours = p_attendance_hours - p_work100
                    payslip.has_attendance_discrepancy = abs(payslip.attendance_discrepancy_hours) > 0.01
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
