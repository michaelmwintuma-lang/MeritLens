"""The five user roles. Every user has exactly one."""

EMPLOYEE = "employee"
MANAGER = "manager"
HR = "hr"
ADMIN = "admin"
FINANCE = "finance"  # signs off the pay rise that comes with an approved promotion

ALL_ROLES = (EMPLOYEE, MANAGER, HR, ADMIN, FINANCE)

# Who uses anonymous reporting. HR handles reports (in the report inbox) and admins manage accounts, so they
# don't report through the system.
REPORTER_ROLES = (EMPLOYEE, MANAGER)
