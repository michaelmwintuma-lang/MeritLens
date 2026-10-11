"""The six user roles. Every user has exactly one."""

EMPLOYEE = "employee"
MANAGER = "manager"
HR = "hr"
ADMIN = "admin"
FINANCE = "finance"  # signs off the pay rise that comes with an approved promotion
# Compliance auditor: read-only oversight of decisions, the model and its fairness, and aggregated feedback.
# Never sees an individual's feedback and can't change anything.
AUDITOR = "auditor"

ALL_ROLES = (EMPLOYEE, MANAGER, HR, ADMIN, FINANCE, AUDITOR)
