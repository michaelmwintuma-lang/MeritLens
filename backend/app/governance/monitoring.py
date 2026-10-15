"""
Live fairness monitoring: the four-fifths rule on what is happening now, not only on the test set at training time.

People can override the model, and the employees being scored change, so fairness at training time doesn't
guarantee fairness in use. Three stages are checked for each characteristic (gender, age band, education):

1. The model:   the share of each group the live model recommends, across today's employee directory.
2. Managers:    the share of each group that managers recommend (nominate) for promotion.
3. HR:          of each group's decided nominations, the share HR approved.

Each stage passes when every group's rate is at least 80% of the highest group's. A ratio under 0.8 is flagged only
when a gap that size is unlikely to be chance (Fisher exact test, p < 0.05); otherwise it is reported as "within
chance": in a directory of 120, a handful of people more or less moves the ratio a lot. A group is only counted
with at least MIN_GROUP people in it (and its rate is never shown otherwise), so no one person's outcome can be
read off. When too few groups are big enough, the answer is "not enough data yet", never a guess. Comparing the stages
shows where a gap appears: in the model, in managers' recommendations, or in HR's decisions.
"""
from collections import defaultdict
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.governance.models import EqualityMonitoring
from app.promotion.models import Decision, Employee, Nomination

FOUR_FIFTHS = 0.8
MIN_GROUP = 5
SIGNIFICANCE = 0.05  # a gap is flagged only when chance alone would produce it less than 5% of the time
CHARACTERISTICS = {"gender": "Gender", "age_band": "Age band", "education_level": "Education"}


def age_band(age: float | None) -> str | None:
    return None if age is None else ("under 40" if age < 40 else "40+")


@lru_cache(maxsize=1)
def dataset_characteristics() -> dict[int, dict]:
    """Gender, age band and education of every employee in the (synthetic) dataset, by id (read once)."""
    from app.promotion.features import load_dataset
    rows = load_dataset()[["employee_id", "gender", "age", "education_level"]]
    return {int(r.employee_id): {"gender": r.gender, "age_band": age_band(r.age), "education_level": r.education_level}
            for r in rows.itertuples()}


def seed_demo_monitoring(db: Session) -> None:
    """The demo employees' characteristics, from their own rows of the dataset, once."""
    if db.scalar(select(EqualityMonitoring).limit(1)) is not None:
        return
    known = dataset_characteristics()
    for employee_id in db.scalars(select(Employee.id)):
        if employee_id in known:
            db.add(EqualityMonitoring(employee_id=employee_id, **known[employee_id]))
    db.commit()


def chance_of_gap(lowest: tuple[int, int], highest: tuple[int, int]) -> float:
    """
    How likely a gap at least this big would be by chance alone, if both groups really had the same rate (two-sided
    Fisher exact test on the lowest and highest groups). With small groups a ratio under 0.8 is often just chance:
    8 of 62 against 4 of 59 is a ratio of 0.53, yet such a gap happens by chance about a third of the time.
    """
    from scipy.stats import fisher_exact
    (low_selected, low_total), (high_selected, high_total) = lowest, highest
    _, p_value = fisher_exact([[high_selected, high_total - high_selected], [low_selected, low_total - low_selected]])
    return float(p_value)


def stage(counts: dict[str, tuple[int, int]], label: str) -> dict:
    """
    counts: group -> (selected, out of). The rate per big-enough group, the ratio, and the verdict:
    - "passes": the ratio is at least 0.8;
    - "below four-fifths": under 0.8, and a gap that size is unlikely to be chance (p < SIGNIFICANCE): look into it;
    - "within chance": under 0.8, but at these group sizes a gap like it happens by chance (p >= SIGNIFICANCE);
    - "not enough data": fewer than two groups of MIN_GROUP or more, or fewer than MIN_GROUP people selected in all.
    """
    groups, rates = [], {}
    for group, (selected, total) in sorted(counts.items()):
        big_enough = total >= MIN_GROUP
        rate = round(selected / total, 4) if big_enough and total else None
        groups.append({"group": group, "count": total if big_enough else None, "rate": rate,
                       "shown": big_enough})
        if rate is not None:
            rates[group] = rate
    selected_in_total = sum(counts[g][0] for g in rates)
    if len(rates) < 2 or selected_in_total < MIN_GROUP:
        # e.g. 3 nominations in all: too few to judge, and a rate like "1 of 36" could point to one person, so
        # no rate is shown at all
        if selected_in_total < MIN_GROUP:
            for g in groups:
                g["rate"] = None
        return {"stage": label, "groups": groups, "ratio": None, "p_value": None, "status": "not enough data"}
    lowest, highest = min(rates, key=rates.get), max(rates, key=rates.get)
    ratio = round(rates[lowest] / rates[highest], 4)
    if ratio >= FOUR_FIFTHS:
        return {"stage": label, "groups": groups, "ratio": ratio, "p_value": None, "status": "passes"}
    p_value = round(chance_of_gap(counts[lowest], counts[highest]), 4)
    return {"stage": label, "groups": groups, "ratio": ratio, "p_value": p_value,
            "status": "below four-fifths" if p_value < SIGNIFICANCE else "within chance"}


def report(db: Session) -> dict:
    from app.promotion.explain import ModelNotTrained, get_model

    people = {m.employee_id: m for m in db.scalars(select(EqualityMonitoring))}
    employees = list(db.scalars(select(Employee)))
    try:
        live = get_model()
        recommended = {e.id: s >= live.threshold for e, s in zip(employees, live.scores([e.record for e in employees]))}
        version = live.version
    except ModelNotTrained:
        recommended, version = {}, None
    nominated = {n.employee_id for n in db.scalars(select(Nomination))}
    decided = {}
    for d in db.scalars(select(Decision)):
        decided[d.employee_id] = d.decision == "approve" or decided.get(d.employee_id, False)

    checks = []
    for key, name in CHARACTERISTICS.items():
        model_counts, nominate_counts, approve_counts = (defaultdict(lambda: [0, 0]) for _ in range(3))
        for e in employees:
            group = getattr(people.get(e.id), key, None) if e.id in people else None
            if group is None:
                continue  # not given: left out, never guessed
            model_counts[group][0] += bool(recommended.get(e.id))
            model_counts[group][1] += 1
            nominate_counts[group][0] += e.id in nominated
            nominate_counts[group][1] += 1
            if e.id in decided:
                approve_counts[group][0] += decided[e.id]
                approve_counts[group][1] += 1
        checks.append({"characteristic": key, "label": name, "stages": [
            stage({g: tuple(v) for g, v in model_counts.items()}, "Model recommends"),
            stage({g: tuple(v) for g, v in nominate_counts.items()}, "Managers nominate"),
            stage({g: tuple(v) for g, v in approve_counts.items()}, "HR approves (of decided)"),
        ]})
    statuses = [s["status"] for c in checks for s in c["stages"]]
    overall = next((s for s in ("below four-fifths", "within chance", "passes") if s in statuses), "not enough data")
    return {"rule": f"each group's rate at least {FOUR_FIFTHS:.0%} of the highest group's; a gap is flagged when "
                    f"it is unlikely to be chance (Fisher exact test, p < {SIGNIFICANCE})",
            "min_group": MIN_GROUP, "employees": len(employees), "with_monitoring_data": len(people),
            "model_version": version, "overall": overall, "checks": checks}
