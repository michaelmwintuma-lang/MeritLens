"""The four user roles. Every user has exactly one."""

EMPLOYEE = "employee"
MANAGER = "manager"
HR = "hr"
ADMIN = "admin"

ALL_ROLES = (EMPLOYEE, MANAGER, HR, ADMIN)

# Who uses anonymous reporting. HR handles reports (in the report inbox) and admins manage accounts, so they
# don't report through the system.
REPORTER_ROLES = (EMPLOYEE, MANAGER)
