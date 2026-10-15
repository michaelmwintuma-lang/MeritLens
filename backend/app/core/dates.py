"""Small date helpers shared by Finance's page and the reminders."""
from datetime import date, timedelta


def working_days_between(start: date, end: date) -> int:
    """Monday-to-Friday days after `start`, up to and including `end` (public holidays aren't known)."""
    days, current = 0, start
    while current < end:
        current += timedelta(days=1)
        days += current.weekday() < 5
    return days
