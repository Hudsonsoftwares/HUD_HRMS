# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models, _

class HudsonAttendanceRawPunch(models.Model):
    _name = 'hudson.attendance.raw.punch'
    _description = 'Biometric Raw Punch Log'
    _order = 'punch_time desc, id desc'

    device_id = fields.Many2one(
        'hudson.attendance.device',
        string='Source Device',
        ondelete='set null',
        help='The biometric device or endpoint that generated this punch.'
    )
    employee_code = fields.Char(
        string='Employee External Code',
        required=True,
        index=True,
        help='The identifier of the employee from the source system/device.'
    )
    punch_time = fields.Datetime(
        string='Punch Timestamp (UTC)',
        required=True,
        index=True,
        help='The timestamp of the punch normalized to UTC.'
    )
    source_timezone = fields.Char(
        string='Source Timezone',
        default='UTC',
        help='The original timezone of the source device when the punch occurred.'
    )
    punch_type = fields.Selection([
        ('in', 'In'),
        ('out', 'Out'),
        ('break_out', 'Break Out'),
        ('break_in', 'Break In'),
        ('overtime_in', 'Overtime In'),
        ('overtime_out', 'Overtime Out')
    ], string='Punch Type', required=True)

    external_uid = fields.Char(
        string='External Unique ID',
        index=True,
        help='Vendor transaction or log unique ID to prevent double ingestion.'
    )
    state = fields.Selection([
        ('new', 'New'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
        ('duplicate', 'Duplicate'),
        ('unmapped', 'Unmapped')
    ], string='State', default='new', required=True, index=True)

    error_message = fields.Text(
        string='Processing Notes/Errors',
        readonly=True
    )
    hr_attendance_id = fields.Many2one(
        'hr.attendance',
        string='Processed Attendance Link',
        ondelete='set null',
        readonly=True,
        help='Link to the Odoo attendance record created or updated by this punch.'
    )

    def action_process_punch(self):
        """Action button to trigger manual processing for selected raw punches."""
        self._process_punch()
        return True

    def _process_punch(self):
        """
        The central process method for raw punches. Resolves employees,
        runs de-duplication, maps punch actions, and projects them safely into hr.attendance.
        """
        for punch in self:
            # Only process if in a non-terminal state
            if punch.state in ('processed', 'duplicate'):
                continue

            # Clear previous error message
            punch.write({'error_message': False})

            try:
                with self.env.cr.savepoint():
                    # 1. Resolve Employee
                    employee = self.env['hr.employee'].search([
                        ('biometric_code', '=', punch.employee_code)
                    ], limit=1)

                    if not employee:
                        # Fallback: check standard Odoo barcode
                        employee = self.env['hr.employee'].search([
                            ('barcode', '=', punch.employee_code)
                        ], limit=1)

                    if not employee:
                        punch.write({
                            'state': 'unmapped',
                            'error_message': _("No employee found with Biometric/Attendance Code or Barcode match: %s") % punch.employee_code
                        })
                        continue

                    # 2. De-duplication Check
                    # Check unique external transaction ID if provided
                    if punch.external_uid:
                        duplicate_uid = self.search([
                            ('external_uid', '=', punch.external_uid),
                            ('id', '!=', punch.id),
                            ('state', 'in', ('processed', 'duplicate'))
                        ], limit=1)
                        if duplicate_uid:
                            punch.write({
                                'state': 'duplicate',
                                'error_message': _("Duplicate check failed: External Unique ID %s already processed.") % punch.external_uid
                            })
                            continue

                    # Check for temporal duplicate (same employee, type, and within 5 seconds)
                    time_margin = 5
                    start_time = punch.punch_time - timedelta(seconds=time_margin)
                    end_time = punch.punch_time + timedelta(seconds=time_margin)

                    duplicate_time = self.search([
                        ('employee_code', '=', punch.employee_code),
                        ('punch_time', '>=', start_time),
                        ('punch_time', '<=', end_time),
                        ('punch_type', '=', punch.punch_type),
                        ('id', '!=', punch.id),
                        ('state', '=', 'processed')
                    ], limit=1)

                    if duplicate_time:
                        punch.write({
                            'state': 'duplicate',
                            'error_message': _("Duplicate check failed: Similar punch already processed for employee at %s.") % punch.punch_time
                        })
                        continue

                    # 3. Categorize punch to action
                    is_check_in = punch.punch_type in ('in', 'break_in', 'overtime_in')
                    is_check_out = punch.punch_type in ('out', 'break_out', 'overtime_out')

                    # Search for any open attendance (check_out is unset)
                    open_attendance = self.env['hr.attendance'].search([
                        ('employee_id', '=', employee.id),
                        ('check_out', '=', False)
                    ], order='check_in desc', limit=1)

                    if is_check_in:
                        if open_attendance:
                            punch.write({
                                'state': 'failed',
                                'error_message': _("Employee %s is already checked in. Open attendance starts at %s.") % (employee.name, open_attendance.check_in)
                            })
                            continue

                        # Create new attendance record
                        new_attendance = self.env['hr.attendance'].with_context(biometric_punch_processing=True).create({
                            'employee_id': employee.id,
                            'check_in': punch.punch_time,
                        })
                        punch.write({
                            'state': 'processed',
                            'hr_attendance_id': new_attendance.id,
                        })

                    elif is_check_out:
                        if not open_attendance:
                            punch.write({
                                'state': 'failed',
                                'error_message': _("No active check-in found for check-out punch of employee %s.") % employee.name
                            })
                            continue

                        if punch.punch_time < open_attendance.check_in:
                            punch.write({
                                'state': 'failed',
                                'error_message': _("Punch time %s is before the active check-in time %s.") % (punch.punch_time, open_attendance.check_in)
                            })
                            continue

                        # Close the existing attendance record
                        open_attendance.with_context(biometric_punch_processing=True).write({
                            'check_out': punch.punch_time,
                        })
                        punch.write({
                            'state': 'processed',
                            'hr_attendance_id': open_attendance.id,
                        })

            except Exception as e:
                # Capture database-level exceptions or validation failures
                punch.write({
                    'state': 'failed',
                    'error_message': _("System error processing punch: %s") % str(e)
                })
