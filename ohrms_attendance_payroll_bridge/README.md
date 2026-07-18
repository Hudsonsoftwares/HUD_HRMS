# OHRMS Attendance Payroll Bridge

This Odoo 19 module connects real attendance records from `hr.attendance` with the scheduled hours in `hr.payslip` computation, warning HR managers of discrepancies.

## Features
- **Discrepancy Detection**: Computes difference between actual checked hours (`hr.attendance`) and scheduled work hours (retains the unmodified `WORK100` line on `hr.payslip`).
- **Discrepancy Indicators**: Displays a warning smart button containing the difference (+/- hours) if the discrepancy exceeds 0.01 hours.
- **Inspect Attendances**: Click on the smart button to view a pre-filtered list of attendance logs for the employee in that payslip period.
- **Filters**: Quickly filter payslips in list and kanban views using the "Attendance Discrepancies" filter.

---

## Testing Workflow

1. **Create Mismatch (Employee A)**:
   - Choose or configure an employee who has a standard working schedule (e.g. 8 hours/day).
   - Log attendance records (`hr.attendance`) for this employee during a given period where the total actual hours are different from their scheduled hours (e.g. logging fewer or more hours than scheduled).
2. **Compute Employee A's Payslip**:
   - Create a new Payslip for Employee A matching the period.
   - Click **Compute Sheet** (or trigger the employee/date onchanges).
   - Verify that:
     - The smart button `Attendance Mismatch` appears in the top-right.
     - The button displays the correct mismatch format, e.g. `+3.5 hrs` or `-2.0 hrs`.
     - `has_attendance_discrepancy` is `True` under-the-hood.
3. **Inspect Attendances**:
   - Click the smart button.
   - Verify it opens the Attendances list view containing only the attendance entries of Employee A during that payslip's start/end dates.
4. **Create Match (Employee B)**:
   - For a second employee, log attendances that match their scheduled working hours exactly.
   - Create a payslip for this employee for the same period and compute it.
   - Verify that `has_attendance_discrepancy` is `False` and no smart button appears.
5. **Verify List Filters**:
   - Go to **Payroll -> Employee Payslips** (list view).
   - Apply the search filter **Attendance Discrepancies**.
   - Verify that only Employee A's payslip is returned, while Employee B's payslip is hidden.
