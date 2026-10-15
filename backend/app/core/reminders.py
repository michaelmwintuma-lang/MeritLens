"""
Reminders: a nudge before something is late, sent once, never repeatedly.

- Managers: in the last 3 days before a review cycle's nomination deadline, if the model recommends people on their
  own team whom they haven't nominated (a count only: the model only advises, and recommending nobody is fine).
- Finance: pay rises that have waited more than 2 working days for sign-off.
- HR: a review cycle whose nominations have closed and are all decided (ready to close), and record corrections
  that have waited more than 3 days.

Each reminder has a key (e.g. "nominations:3:7" for cycle 3, manager 7) kept in ReminderSent, so it goes out once.
The scheduler (scheduler.py) runs them every hour; the admin can also run them from the Email page.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.accounts.contacts import finance_contacts, hr_contacts
from app.accounts.models import User
from app.core import email_templates as templates
from app.core import mailer
from app.core.database import Base
from app.core.dates import working_days_between
from app.core.roles import MANAGER
from app.feedback.models import CorrectionRequest
from app.promotion import cycles
from app.promotion.models import CycleScore, Decision, Employee, Nomination, PayReview

NOMINATION_DAYS = 3      # remind managers this many days before the deadline (and on the day)
PAY_WORKING_DAYS = 2     # remind Finance about pay rises waiting longer than this
CORRECTION_DAYS = 3      # remind HR about corrections waiting longer than this


class ReminderSent(Base):
    __tablename__ = "reminders_sent"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


def first_time(db: Session, key: str) -> bool:
    """True (and remembered) the first time a reminder with this key is due; False ever after."""
    if db.scalar(select(ReminderSent).where(ReminderSent.key == key)) is not None:
        return False
    db.add(ReminderSent(key=key))
    return True


def run_due(db: Session, today: date | None = None) -> list[str]:
    """Send every reminder that is due and hasn't been sent. Returns what was sent, in words."""
    today = today or date.today()
    outbox: list[tuple[str, dict]] = []
    sent: list[str] = []

    # Managers, before a cycle's nomination deadline
    cycle = cycles.open_cycle(db)
    if cycle is not None and cycle.nominations_close is not None and 0 <= (cycle.nominations_close - today).days <= NOMINATION_DAYS:
        nominated = {n.employee_id for n in db.scalars(select(Nomination).where(Nomination.cycle_id == cycle.id))}
        waiting: dict[int, int] = {}
        for score, employee in db.execute(select(CycleScore, Employee).join(Employee, Employee.id == CycleScore.employee_id)
                                          .where(CycleScore.cycle_id == cycle.id, CycleScore.recommended.is_(True))):
            if employee.manager_user_id and employee.id not in nominated:
                waiting[employee.manager_user_id] = waiting.get(employee.manager_user_id, 0) + 1
        for manager_id, count in waiting.items():
            manager = db.get(User, manager_id)
            if manager and manager.is_active and manager.role == MANAGER and manager.email and first_time(db, f"nominations:{cycle.id}:{manager_id}"):
                outbox.append((manager.email, templates.reminder_nominations(
                    manager.full_name, cycle.name, count, cycle.nominations_close.isoformat(), (cycle.nominations_close - today).days)))
                sent.append(f"{manager.full_name}: nominations for {cycle.name}")

    # Finance, pay rises waiting more than two working days (since they last reached Finance)
    overdue = []
    for decision in db.scalars(select(Decision).where(Decision.pay_status == "awaiting_finance")):
        step = db.scalar(select(PayReview).where(PayReview.decision_id == decision.id, PayReview.action.in_(("submitted", "resubmitted")))
                         .order_by(PayReview.at.desc(), PayReview.id.desc()).limit(1))
        if step and working_days_between(step.at.date(), today) > PAY_WORKING_DAYS and first_time(db, f"pay:{decision.id}:{step.id}"):
            overdue.append(db.get(Employee, decision.employee_id).full_name)
    if overdue:
        for email, name in finance_contacts(db):
            outbox.append((email, templates.reminder_pay_waiting(name, sorted(overdue))))
        sent.append(f"Finance: {len(overdue)} pay rise(s) waiting")

    # HR, a cycle ready to close
    if cycle is not None and not cycles.nominations_open(cycle, today) and cycles.progress(db, cycle, with_people=False)["can_close"] \
            and first_time(db, f"cycle-ready:{cycle.id}"):
        for email, name in hr_contacts(db):
            outbox.append((email, templates.reminder_cycle_ready(name, cycle.name)))
        sent.append(f"HR: {cycle.name} is ready to close")

    # HR, corrections waiting more than three days (one reminder per request)
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=CORRECTION_DAYS)
    late = [r.id for r in db.scalars(select(CorrectionRequest).where(CorrectionRequest.status == "pending",
                                                                     CorrectionRequest.created_at <= cutoff))]
    late = [r for r in late if first_time(db, f"correction:{r}")]
    if late:
        for email, name in hr_contacts(db):
            outbox.append((email, templates.reminder_corrections_waiting(name, len(late))))
        sent.append(f"HR: {len(late)} correction(s) waiting")

    db.commit()  # remember what was sent before sending, so a slow mail server never causes a second reminder
    for email, mail in outbox:
        mailer.send(email, mail)
    return sent
