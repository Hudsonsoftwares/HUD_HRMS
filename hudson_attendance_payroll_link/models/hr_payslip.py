# -*- coding: utf-8 -*-
import pytz
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_attendance_vs_schedule(self, contract, date_from, date_to):
        """
        Calculates scheduled, actual, shortage, and unpaid leave hours on a 
        day-by-day basis to reconcile shortages and unpaid leaves, 
        ensuring they are mutually exclusive.
        """
        if not hasattr(self.env, '_attendance_cache'):
            self.env._attendance_cache = {}
        cache_key = (contract.id, date_from, date_to)
        if cache_key in self.env._attendance_cache:
            return self.env._attendance_cache[cache_key]

        # 1. Setup timezone and datetime boundaries
        calendar = contract.resource_calendar_id
        tz = pytz.timezone(calendar.tz or 'UTC') if calendar else pytz.UTC
        
        day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
        day_to = datetime.combine(fields.Date.from_string(date_to), time.max)
        
        # 2. Query all attendances in the period
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', contract.employee_id.id),
            ('check_in', '>=', day_from),
            ('check_in', '<=', day_to),
        ])
        
        # Group attendances by their local check_in date
        attendances_by_date = {}
        for att in attendances:
            local_check_in = pytz.utc.localize(att.check_in).astimezone(tz)
            att_date = local_check_in.date()
            attendances_by_date.setdefault(att_date, []).append(att)
            
        # 3. Query all applied regularizations in the period
        regularizations = self.env['hudson.attendance.regularization'].search([
            ('employee_id', '=', contract.employee_id.id),
            ('state', '=', 'applied'),
            ('attendance_id.check_in', '>=', day_from),
            ('attendance_id.check_in', '<=', day_to),
        ])
        
        regularized_dates = set()
        for reg in regularizations:
            if reg.attendance_id:
                local_check_in = pytz.utc.localize(reg.attendance_id.check_in).astimezone(tz)
                regularized_dates.add(local_check_in.date())

        # 4. Get leave intervals using Odoo's native list_leaves method
        unpaid_hours_by_date = {}
        paid_hours_by_date = {}
        
        if calendar:
            day_leave_intervals = contract.employee_id.list_leaves(
                day_from, day_to, calendar=calendar
            )
            for day, hours, leave in day_leave_intervals:
                is_unpaid = False
                for l in leave:
                    if l.holiday_id and l.holiday_id.holiday_status_id.unpaid:
                        is_unpaid = True
                        break
                if is_unpaid:
                    unpaid_hours_by_date[day] = unpaid_hours_by_date.get(day, 0.0) + hours
                else:
                    paid_hours_by_date[day] = paid_hours_by_date.get(day, 0.0) + hours

        # 5. Day-by-day scheduled vs actual audit loop
        total_scheduled_hours = 0.0
        total_actual_hours = 0.0
        total_shortage_hours = 0.0
        total_unpaid_hours = 0.0
        total_unpaid_days = 0.0
        
        current_date = fields.Date.from_string(date_from)
        end_date = fields.Date.from_string(date_to)
        
        while current_date <= end_date:
            # Scheduled work hours for the day
            scheduled_hours = 0.0
            if calendar:
                day_start = tz.localize(datetime.combine(current_date, time.min))
                day_end = tz.localize(datetime.combine(current_date, time.max))
                scheduled_hours = calendar.get_work_hours_count(day_start, day_end, compute_leaves=False)
            
            total_scheduled_hours += scheduled_hours
            
            # Actual worked hours for the day
            day_atts = attendances_by_date.get(current_date, [])
            actual_hours = sum(att.worked_hours for att in day_atts)
            total_actual_hours += actual_hours
            
            unpaid_leave_hours = unpaid_hours_by_date.get(current_date, 0.0)
            paid_leave_hours = paid_hours_by_date.get(current_date, 0.0)
            
            # Unpaid leave accounting
            if unpaid_leave_hours > 0.0:
                total_unpaid_hours += unpaid_leave_hours
                std_hours = contract.standard_hours_per_day or 8.0
                denom = scheduled_hours if scheduled_hours > 0.0 else std_hours
                total_unpaid_days += unpaid_leave_hours / denom
            
            # Shortage reconciliation
            is_regularized = current_date in regularized_dates
            if is_regularized:
                # Regularized day: no shortage is deducted
                shortage_hours = 0.0
            else:
                # Leave takes priority, subtract leave hours from scheduled hours for shortage calculation
                remaining_scheduled = max(scheduled_hours - paid_leave_hours - unpaid_leave_hours, 0.0)
                shortage_hours = max(remaining_scheduled - actual_hours, 0.0)
                
            total_shortage_hours += shortage_hours
            current_date += relativedelta(days=1)

        # 6. Overtime calculation
        approved_attendances = attendances.filtered(lambda a: a.overtime_status == 'approved')
        validated_overtime_hours = sum(approved_attendances.mapped('validated_overtime_hours'))
        
        data = {
            'scheduled_hours': total_scheduled_hours,
            'actual_hours': total_actual_hours,
            'validated_overtime_hours': validated_overtime_hours,
            'overtime_hours_delta': validated_overtime_hours,
            'shortage_hours_delta': total_shortage_hours,
            'unpaid_hours': total_unpaid_hours,
            'unpaid_days': total_unpaid_days,
        }
        
        self.env._attendance_cache[cache_key] = data
        return data

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        res = super(HrPayslip, self).get_worked_day_lines(contracts, date_from, date_to)
        for contract in contracts:
            data = self._get_attendance_vs_schedule(contract, date_from, date_to)
            if data.get('unpaid_days', 0.0) > 0.01:
                res.append({
                    'name': _('Unpaid Leave'),
                    'sequence': 4,
                    'code': 'UNPAID',
                    'number_of_days': data['unpaid_days'],
                    'number_of_hours': data['unpaid_hours'],
                    'contract_id': contract.id,
                })
        return res
