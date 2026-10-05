"""
Score the user test: the System Usability Scale (SUS) questionnaire, extra questions about explanations and trust,
and the tasks people completed.

Fill in evaluation/user_test_sus.csv and evaluation/user_test_tasks.csv (one row per participant / per task), then
run from the backend folder:   python -m evaluation.user_test
Results are saved to results/user_test.md. With no rows filled in, it says so and saves nothing.

SUS (Brooke, 1996): ten statements answered 1 (strongly disagree) to 5 (strongly agree). Odd statements are
positive, even ones negative, so: odd -> answer - 1, even -> 5 - answer, total x 2.5 = a score from 0 to 100.
68 is the average across hundreds of published studies (Sauro, 2011), so above 68 is better than average.
"""
import csv
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parents[1] / "results"
SUS_FILE, TASKS_FILE = HERE / "user_test_sus.csv", HERE / "user_test_tasks.csv"
EXTRA = {
    "e1": "The explanations helped me understand why a readiness score was what it was.",
    "e2": "I would trust a promotion decision made with this system's advice.",
    "e3": "When reporting, I felt my identity was protected.",
    "e4": "I could find what I needed without help.",
}


def sus_score(answers: list[int]) -> float:
    """One person's SUS score (0-100) from their ten answers (each 1-5)."""
    if len(answers) != 10 or any(a not in (1, 2, 3, 4, 5) for a in answers):
        raise ValueError("SUS needs ten answers, each from 1 to 5.")
    return sum((a - 1) if i % 2 == 0 else (5 - a) for i, a in enumerate(answers)) * 2.5


def grade(score: float) -> str:
    """Where a SUS score sits on the Sauro-Lewis curved grading scale."""
    for bound, letter in [(84.1, "A+"), (80.8, "A"), (78.9, "A-"), (77.2, "B+"), (74.1, "B"), (72.6, "B-"),
                          (71.1, "C+"), (65.0, "C"), (62.7, "C-"), (51.7, "D")]:
        if score >= bound:
            return letter
    return "F"


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f) if any((v or "").strip() for v in row.values())]


def main():
    sus_rows, task_rows = read_rows(SUS_FILE), read_rows(TASKS_FILE)
    if not sus_rows:
        print("No answers yet: fill in evaluation/user_test_sus.csv (one row per participant), then run this again.")
        return

    scores = {row["participant"]: sus_score([int(row[f"q{i}"]) for i in range(1, 11)]) for row in sus_rows}
    values = list(scores.values())
    mean = statistics.mean(values)
    lines = ["# User test results", "",
             f"Produced by `python -m evaluation.user_test` from {len(values)} participants' answers. "
             "Method: `docs/USER_TEST.md`.", "",
             "## System Usability Scale", "",
             f"- Mean SUS score: **{mean:.1f}** (grade {grade(mean)}; the published average is 68)",
             f"- Median {statistics.median(values):.1f}, lowest {min(values):.1f}, highest {max(values):.1f}"
             + (f", standard deviation {statistics.stdev(values):.1f}" if len(values) > 1 else ""), "",
             "| Participant | Role played | SUS | Grade |", "|---|---|---|---|"]
    for row in sus_rows:
        s = scores[row["participant"]]
        lines.append(f"| {row['participant']} | {row.get('role_played', '')} | {s:.1f} | {grade(s)} |")

    lines += ["", "## Explanations and trust (1 = strongly disagree, 5 = strongly agree)", "",
              "| Statement | Answers | Mean | Agree (4-5) |", "|---|---|---|---|"]
    for key, statement in EXTRA.items():
        answers = [int(row[key]) for row in sus_rows if (row.get(key) or "").strip()]
        if answers:
            agree = sum(a >= 4 for a in answers)
            lines.append(f"| {statement} | {len(answers)} | {statistics.mean(answers):.1f} | {agree} of {len(answers)} |")

    if task_rows:
        by_task = defaultdict(list)
        for row in task_rows:
            by_task[row["task"]].append(row)
        lines += ["", "## Tasks", "", "| Task | Tried | Completed alone | With help | Not completed | Median time (s) |",
                  "|---|---|---|---|---|---|"]
        for task, rows in by_task.items():
            outcome = [r["completed"].strip().lower() for r in rows]
            times = [float(r["seconds"]) for r in rows if (r.get("seconds") or "").strip() and r["completed"].strip().lower() != "no"]
            lines.append(f"| {task} | {len(rows)} | {outcome.count('yes')} | {outcome.count('help')} | {outcome.count('no')} | "
                         f"{statistics.median(times):.0f} |" if times else
                         f"| {task} | {len(rows)} | {outcome.count('yes')} | {outcome.count('help')} | {outcome.count('no')} | – |")

    comments = [(row["participant"], row["comments"].strip()) for row in sus_rows if (row.get("comments") or "").strip()]
    if comments:
        lines += ["", "## Comments", ""] + [f"- {who}: “{text}”" for who, text in comments]

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "user_test.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(values)} participants, mean SUS {mean:.1f} ({grade(mean)}). Saved results/user_test.md")


if __name__ == "__main__":
    main()
