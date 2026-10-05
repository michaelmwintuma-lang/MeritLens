"""
Evaluate the reporting part: how well the anonymiser removes identifying details, how well it flags phrases that
could identify the reporter, and how well triage sets the priority.

Run from the backend folder:   python -m evaluation.evaluate_reporting

It reads every labelled set in this folder (reports_developer.json, and reports_external.json once it has reports
written by other people), runs the real anonymiser and triage on each report, compares with the labels, and saves
the results to results/reporting_evaluation.json and results/reporting_evaluation.md. Every number comes from
running the code; the labels and how they were made are explained in docs/EVALUATION.md.
"""
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from app.promotion.seed import unique_names
from app.reporting.anonymiser import anonymise
from app.reporting.triage import LEVELS, triage

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parents[1] / "results"
SETS = [("developer", HERE / "reports_developer.json"), ("external", HERE / "reports_external.json")]
TYPES = ["name", "email", "phone", "date"]

# The same directory the demo app uses: the 120 generated employees and the four demo accounts
DIRECTORY = unique_names(120) + ["Ada Admin", "Hana Reviewer", "Mo Manager", "Eli Employee"]


# ─── Matching a label against the system's output ─────────────────────────────
def name_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z]+", text) if len(w) > 2]


def is_removed(kind: str, original: str, cleaned: str) -> bool:
    """Has this labelled detail gone from the cleaned text?"""
    if kind == "name":  # every word of the name must be gone (a half-removed name still leaks)
        return all(not re.search(rf"\b{re.escape(w)}\b", cleaned, re.IGNORECASE) for w in name_words(original))
    if kind == "phone":  # every group of 3+ digits must be gone
        return all(group not in cleaned for group in re.findall(r"\d{3,}", original))
    return original.lower() not in cleaned.lower()


def overlaps(a: str, b: str) -> bool:
    """Do two snippets refer to the same thing? (one contains the other, or they share a name word or digit group)"""
    a_low, b_low = a.lower(), b.lower()
    if a_low in b_low or b_low in a_low:
        return True
    if set(w.lower() for w in name_words(a)) & set(w.lower() for w in name_words(b)):
        return True
    return bool(set(re.findall(r"\d{3,}", a)) & set(re.findall(r"\d{3,}", b)))


def safe_div(a, b):
    return round(a / b, 3) if b else None


# ─── Evaluating one labelled set ──────────────────────────────────────────────
def evaluate(reports: list[dict]) -> dict:
    found, total = Counter(), Counter()                  # labelled details removed / labelled
    right_swaps, all_swaps = Counter(), Counter()        # replacements that were sensitive / all replacements
    leaks, wrong_swaps = [], []
    flags_found = flags_total = flags_right = flags_all = 0
    missed_flags, wrong_flags = [], []
    fully_clean = 0
    confusion = {truth: {guess: 0 for guess in LEVELS} for truth in LEVELS}
    triage_misses = []

    for r in reports:
        result = anonymise(r["text"], DIRECTORY)
        cleaned = result["text"]

        # Anonymiser: did each labelled detail go?
        clean = True
        for kind, original in r["sensitive"]:
            total[kind] += 1
            if is_removed(kind, original, cleaned):
                found[kind] += 1
            else:
                clean = False
                leaks.append({"id": r["id"], "type": kind, "detail": original, "note": r.get("note", "")})
        fully_clean += clean

        # Anonymiser: was each replacement something that should have gone?
        for swap in result["replaced"]:
            all_swaps[swap["type"]] += 1
            if any(overlaps(swap["original"], original) for _, original in r["sensitive"]):
                right_swaps[swap["type"]] += 1
            else:
                wrong_swaps.append({"id": r["id"], "type": swap["type"], "removed": swap["original"], "note": r.get("note", "")})

        # Warnings about phrases that could identify the reporter
        warned = [w["phrase"] for w in result["warnings"]]
        for phrase in r["identifying"]:
            flags_total += 1
            if any(overlaps(phrase, w) for w in warned):
                flags_found += 1
            else:
                missed_flags.append({"id": r["id"], "phrase": phrase, "note": r.get("note", "")})
        for w in warned:
            flags_all += 1
            if any(overlaps(phrase, w) for phrase in r["identifying"]):
                flags_right += 1
            else:
                wrong_flags.append({"id": r["id"], "phrase": w})

        # Triage runs on the anonymised text, as in the app
        verdict = triage(cleaned, r["category"])
        guess = verdict["priority"]
        confusion[r["priority"]][guess] += 1
        if guess != r["priority"]:
            words = [t["word"] for t in verdict["triggers"]]
            triage_misses.append({"id": r["id"], "expected": r["priority"], "got": guess,
                                  "words_found": words, "text": r["text"]})

    n = len(reports)
    per_class = {level: {
        "precision": safe_div(confusion[level][level], sum(confusion[t][level] for t in LEVELS)),
        "recall": safe_div(confusion[level][level], sum(confusion[level].values())),
        "count": sum(confusion[level].values()),
    } for level in LEVELS}
    under = sum(confusion[t][g] for t in LEVELS for g in LEVELS if LEVELS.index(g) < LEVELS.index(t))
    over = sum(confusion[t][g] for t in LEVELS for g in LEVELS if LEVELS.index(g) > LEVELS.index(t))

    return {
        "reports": n,
        "anonymiser": {
            "by_type": {k: {"labelled": total[k], "removed": found[k], "recall": safe_div(found[k], total[k]),
                            "replacements": all_swaps[k], "precision": safe_div(right_swaps[k], all_swaps[k])} for k in TYPES},
            "overall": {"labelled": sum(total.values()), "removed": sum(found.values()),
                        "recall": safe_div(sum(found.values()), sum(total.values())),
                        "replacements": sum(all_swaps.values()),
                        "precision": safe_div(sum(right_swaps.values()), sum(all_swaps.values()))},
            "reports_fully_clean": fully_clean,
            "reports_with_details": sum(1 for r in reports if r["sensitive"]),
            "leaks": leaks,
            "wrongly_removed": wrong_swaps,
        },
        "warnings": {"labelled": flags_total, "flagged": flags_found, "recall": safe_div(flags_found, flags_total),
                     "warnings_shown": flags_all, "precision": safe_div(flags_right, flags_all),
                     "missed": missed_flags, "unnecessary": wrong_flags},
        "triage": {"accuracy": safe_div(sum(confusion[l][l] for l in LEVELS), n), "confusion": confusion,
                   "per_class": per_class, "under_triaged": under, "over_triaged": over, "mistakes": triage_misses},
    }


# ─── Writing the results ──────────────────────────────────────────────────────
def pct(x):
    return "–" if x is None else f"{x * 100:.0f}%"


def markdown(name: str, about: str, res: dict) -> str:
    a, w, t = res["anonymiser"], res["warnings"], res["triage"]
    lines = [f"## {name.capitalize()} set ({res['reports']} reports)", "", about, "",
             "### Anonymiser: identifying details", "",
             "| Detail | Labelled | Removed | Recall | Replacements made | Precision |", "|---|---|---|---|---|---|"]
    for k in TYPES:
        b = a["by_type"][k]
        lines.append(f"| {k.capitalize()} | {b['labelled']} | {b['removed']} | {pct(b['recall'])} | {b['replacements']} | {pct(b['precision'])} |")
    o = a["overall"]
    lines += [f"| **All** | **{o['labelled']}** | **{o['removed']}** | **{pct(o['recall'])}** | **{o['replacements']}** | **{pct(o['precision'])}** |", "",
              f"Reports with every labelled detail removed: **{a['reports_fully_clean']} of {res['reports']}** "
              f"({a['reports_with_details']} reports contained at least one detail).", ""]
    if a["leaks"]:
        lines += ["**Missed (left in the text):**", ""] + [f"- {x['id']} ({x['type']}): `{x['detail']}`" + (f" — {x['note']}" if x["note"] else "") for x in a["leaks"]] + [""]
    if a["wrongly_removed"]:
        lines += ["**Removed but not identifying:**", ""] + [f"- {x['id']} ({x['type']}): `{x['removed']}`" + (f" — {x['note']}" if x["note"] else "") for x in a["wrongly_removed"]] + [""]
    lines += ["### Warnings about phrases that could identify the reporter", "",
              f"Flagged {w['flagged']} of {w['labelled']} labelled phrases (recall {pct(w['recall'])}); "
              f"{w['warnings_shown']} warnings shown, of which {pct(w['precision'])} were labelled phrases (precision).", ""]
    if w["missed"]:
        lines += ["**Not flagged:**", ""] + [f"- {x['id']}: “{x['phrase']}”" for x in w["missed"]] + [""]
    if w["unnecessary"]:
        lines += ["**Flagged but not identifying:**", ""] + [f"- {x['id']}: “{x['phrase']}”" for x in w["unnecessary"]] + [""]
    lines += ["### Triage", "", f"Accuracy: **{pct(t['accuracy'])}**. Under-triaged (given a lower priority than it needed): "
              f"**{t['under_triaged']}**. Over-triaged: {t['over_triaged']}.", "",
              "| Expected ↓ / Given → | Low | Medium | High | Recall |", "|---|---|---|---|---|"]
    for truth in LEVELS:
        row = t["confusion"][truth]
        lines.append(f"| {truth.capitalize()} | {row['low']} | {row['medium']} | {row['high']} | {pct(t['per_class'][truth]['recall'])} |")
    lines.append("| **Precision** | " + " | ".join(pct(t["per_class"][l]["precision"]) for l in LEVELS) + " | |")
    lines.append("")
    if t["mistakes"]:
        lines += ["**Mistakes** (with the warning words triage found):", ""] + [
            f"- {x['id']}: expected **{x['expected']}**, got {x['got']} ({', '.join(x['words_found']) or 'no warning words'}). "
            f"“{x['text']}”" for x in t["mistakes"]] + [""]
    return "\n".join(lines)


def main():
    output, sections = {"run_on": date.today().isoformat(), "directory_size": len(DIRECTORY)}, []
    for name, path in SETS:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data["reports"]:
            print(f"{name}: no reports yet, skipped")
            continue
        res = evaluate(data["reports"])
        output[name] = res
        sections.append(markdown(name, data["about"], res))
        o, w, t = res["anonymiser"]["overall"], res["warnings"], res["triage"]
        print(f"{name}: {res['reports']} reports | anonymiser recall {pct(o['recall'])}, precision {pct(o['precision'])} | "
              f"warnings recall {pct(w['recall'])}, precision {pct(w['precision'])} | triage accuracy {pct(t['accuracy'])}, "
              f"under-triaged {t['under_triaged']}")
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "reporting_evaluation.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    header = ["# Reporting evaluation", "",
              f"Produced by `python -m evaluation.evaluate_reporting` on {output['run_on']}. Every number comes from running "
              "the real anonymiser and triage on hand-labelled reports. How the labels were made: `docs/EVALUATION.md`.", "",
              "*Recall* = share of the things that should be caught that were caught. *Precision* = share of what the "
              "system caught that should have been caught.", ""]
    (RESULTS / "reporting_evaluation.md").write_text("\n".join(header + sections), encoding="utf-8")
    print("Saved results/reporting_evaluation.json and results/reporting_evaluation.md")


if __name__ == "__main__":
    main()
