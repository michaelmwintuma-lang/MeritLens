# Evaluating the reporting part

The promotion model is evaluated in `results/metrics.json` and `results/fairness.json`. This document covers the
other half: **how well the anonymiser and triage work**. Run it from the `backend` folder:

```
python -m evaluation.evaluate_reporting
```

It runs the real anonymiser and triage on hand-labelled reports and writes `results/reporting_evaluation.md` (for
reading) and `results/reporting_evaluation.json` (every number). Code: `backend/evaluation/evaluate_reporting.py`.

## What is measured

| Part | Question | Measure |
|---|---|---|
| Anonymiser | Of the identifying details in a report, how many are removed? | **Recall** per type (names, emails, phones, dates) |
| Anonymiser | Of what it removes, how much really was identifying? | **Precision** per type |
| Anonymiser | How many reports end up with nothing left to identify anyone? | Reports fully clean |
| Warnings | Of the phrases that could identify the reporter, how many are flagged? Of the warnings, how many are right? | Recall and precision |
| Triage | Does it give the right priority? | Accuracy, a confusion matrix, and the number **under-triaged** (given a lower priority than needed, the costly mistake) |

For the anonymiser, recall matters most: a missed name can expose someone, while an unnecessary replacement only
makes the text a little harder to read (and the reporter sees and can edit the result before sending).

## How the reports were labelled

Each labelled report (`backend/evaluation/reports_*.json`) records the text, its category, and:

- **sensitive**: every detail that should be removed, copied exactly from the text, with its type:
  - *name*: any person's name, full, first or last name alone, nickname, inside or outside the organisation;
  - *email*: any email address, however written;
  - *phone*: any phone number or extension;
  - *date*: a specific calendar day ("12/03/2025", "3rd of May", "Friday the 13th"). Relative times ("last
    week", "yesterday") are not labelled, as they don't name a day.
- **identifying**: phrases that could narrow down who the reporter is (being the only one of a group, when they
  joined, their role, personal circumstances, where they sit).
- **priority**, decided from the content, using the organisation's rules from the brief:
  - *high*: violence or a threat of it, sexual assault or unwanted touching, stalking, weapons, risk of self-harm,
    or a serious danger to safety; and every safety report (the brief's minimum);
  - *medium*: harassment, bullying, discrimination, intimidation, retaliation, fraud or theft; and every
    harassment or discrimination report (the brief's minimum);
  - *low*: everything else.

A test (`tests/test_evaluation_data.py`) checks every label is copied exactly from its report, so a typo can't
distort the results.

## Two sets, and why

1. **Developer set** (`reports_developer.json`, 50 reports): written by the developer. It deliberately includes
   hard cases (nicknames, people outside the organisation, lower-case names, emails written in words, a date
   without a month, threats without the word "threat", figures of speech like "kill the competition"). But the
   developer also wrote the rules, so this set is **likely to flatter the system**.
2. **External set** (`reports_external.json`, empty until you add to it): reports written by people who haven't
   seen the rules. This is the fairer test, and the evaluation reports it separately.

**To collect the external set:** ask 5 to 10 people (classmates are fine) to each write 3 to 5 short, made-up
workplace concerns, the way they would really write them, across different categories. Tell them they may
mention made-up colleagues, contact details and dates; give them a few names from the demo directory to use
(e.g. George Quinn, Nadia Varga, Samuel Patel) and let them invent others. Don't show them the rules. Then label
each report as above, ideally with a second person labelling the same reports so you can compare and settle
disagreements. Add them to `reports_external.json` and run the evaluation again.

## Results (developer set)

From `results/reporting_evaluation.md`, run on 5 October 2026:

| | Result |
|---|---|
| Anonymiser recall (all details) | 87% (41 of 47); names 91%, emails 67%, phones 80%, dates 86% |
| Anonymiser precision | 87% (41 of 47 replacements were identifying) |
| Reports with every detail removed | 44 of 50 |
| Identifying-phrase warnings | recall 91% (10 of 11), precision 91% |
| Triage accuracy | 74% (37 of 50) |
| Under-triaged | 12, including a report about thoughts of self-harm marked **low** |
| Over-triaged | 1 ("kill the competition" marked high) |

### What the results show

- **The anonymiser catches what its rules describe and misses what they don't:** nicknames ("Sam"), people
  outside the organisation ("Derek Holt"), first names written in lower case, emails written in words, short
  extensions, dates without a month. This is the expected weakness of a rule-based approach, and why the
  reporter always reviews the cleaned text before sending.
- **Its unnecessary replacements are harmless but visible:** invoice and version numbers taken for phone numbers,
  and capitalised words that are also parts of directory names ("Manager", "Admin", "Employee").
- **Triage is the weaker part.** A keyword list misses meaning: a threat phrased without the word ("he will make
  sure I regret it"), unwanted touching described politely, self-harm described indirectly, and other forms of a
  listed word ("belittling" when only "belittled" is listed). Most mistakes put a report *lower* than it should be,
  which is the costly direction. The category minimums help (every safety report is high), but an "Other" report
  about self-harm was marked low.
- This is why HR can always change the priority, and why triage is presented as a **suggestion with its
  reasons**, never a decision.

### Improving it, fairly

The obvious fixes (more word forms, phrases like "regret it", "ending my life", "touched me") would raise these
numbers, but **only on this set**, because the fixes would be written while looking at it. A fair improvement
would be made using the developer set, then measured on the **external** set, which the fixes never saw.
Alternatively, a trained text classifier could replace the keyword list, at the cost of being harder to explain.
