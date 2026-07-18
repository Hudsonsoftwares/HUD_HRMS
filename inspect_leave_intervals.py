# Print leaves in database
employee = env['hr.employee'].search([('name', '=', 'Test Overtime Employee')], limit=1)
resource = employee.resource_id

from datetime import datetime
from pytz import timezone, utc

tz = timezone(employee._get_tz() or 'UTC')
date_val = datetime(2026, 7, 15).date()
start_dt_local = tz.localize(datetime.combine(date_val, datetime.min.time()))
end_dt_local = tz.localize(datetime.combine(date_val, datetime.max.time()))

start_dt = start_dt_local.astimezone(utc)
end_dt = end_dt_local.astimezone(utc)

# Let's query resource.calendar.leaves (resource leaves)
leaves = env['resource.calendar.leaves'].search([
    ('resource_id', '=', resource.id),
])
print("Resource Leaves count:", len(leaves))
for l in leaves:
    print(f"  Leave: {l.name}, from {l.date_from} to {l.date_to}, calendar={l.calendar_id.name}")
    
# Let's query hr.leave
hr_leaves = env['hr.leave'].search([
    ('employee_id', '=', employee.id),
])
print("HR Leaves count:", len(hr_leaves))
for l in hr_leaves:
    print(f"  HR Leave: {l.name}, from {l.date_from} to {l.date_to}, state={l.state}")
