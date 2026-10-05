# Reporting evaluation

Produced by `python -m evaluation.evaluate_reporting` on 2026-10-05. Every number comes from running the real anonymiser and triage on hand-labelled reports. How the labels were made: `docs/EVALUATION.md`.

*Recall* = share of the things that should be caught that were caught. *Precision* = share of what the system caught that should have been caught.

## Developer set (50 reports)

Made-up reports labelled by hand to evaluate the anonymiser and triage. Written by the developer, who also wrote the rules, so this set is likely to flatter the system: see reports_external.json for reports written by other people. Labelling rules: docs/EVALUATION.md.

### Anonymiser: identifying details

| Detail | Labelled | Removed | Recall | Replacements made | Precision |
|---|---|---|---|---|---|
| Name | 32 | 29 | 91% | 32 | 91% |
| Email | 3 | 2 | 67% | 2 | 100% |
| Phone | 5 | 4 | 80% | 9 | 67% |
| Date | 7 | 6 | 86% | 4 | 100% |
| **All** | **47** | **41** | **87%** | **47** | **87%** |

Reports with every labelled detail removed: **44 of 50** (37 reports contained at least one detail).

**Missed (left in the text):**

- D15 (name): `Sam` — Nickname for Samuel: not in the directory as written.
- D16 (name): `Derek Holt` — Someone outside the organisation: not in the directory.
- D19 (name): `nadia` — First name alone in lower case.
- D31 (phone): `ext. 4471` — A four-digit internal extension can identify someone, but it is too short for the phone rule.
- D40 (date): `Friday the 13th` — A date without a month; 'my desk' doesn't identify anyone here.
- D41 (email): `nadia at company dot com` — An email address written out in words.

**Removed but not identifying:**

- D06 (phone): `20250114` — Invoice and ticket numbers look like phone numbers but are not personal details.
- D06 (phone): `4471229` — Invoice and ticket numbers look like phone numbers but are not personal details.
- D21 (name): `Manager` — 'Manager' is a job title here, but also part of a demo account's name.
- D25 (phone): `3.14.207` — A version number and 'Admin' with a capital letter: neither is personal.
- D25 (name): `Admin` — A version number and 'Admin' with a capital letter: neither is personal.
- D39 (name): `Employee` — 'Employee' with a capital letter is also part of a demo account's name.

### Warnings about phrases that could identify the reporter

Flagged 10 of 11 labelled phrases (recall 91%); 11 warnings shown, of which 91% were labelled phrases (precision).

**Not flagged:**

- D50: “sit by the window”

**Flagged but not identifying:**

- D40: “my desk”

### Triage

Accuracy: **74%**. Under-triaged (given a lower priority than it needed): **12**. Over-triaged: 1.

| Expected ↓ / Given → | Low | Medium | High | Recall |
|---|---|---|---|---|
| Low | 10 | 0 | 1 | 91% |
| Medium | 8 | 17 | 0 | 68% |
| High | 1 | 3 | 10 | 71% |
| **Precision** | 53% | 85% | 91% | |

**Mistakes** (with the warning words triage found):

- D06: expected **medium**, got low (no warning words). “I believe Samuel Varga is approving his own expense claims. You can check invoice 20250114 and ticket 4471229 in the system.”
- D08: expected **high**, got medium (no warning words). “A colleague touched me inappropriately at the Christmas party and later sent messages to my personal number 07700 900123 asking me to meet him alone.”
- D12: expected **low**, got high (kill). “The new product launch is going to kill the competition, but the marketing team is working until midnight every day and people are exhausted.”
- D15: expected **medium**, got low (no warning words). “Sam keeps belittling my work in front of clients. Everyone calls him Sam but his full name is in the directory.”
- D22: expected **high**, got medium (no warning words). “Mateo Adeyemi said that if I report him he will make sure I regret it, and he knows where I live.”
- D26: expected **medium**, got low (no warning words). “Ibrahim Walsh constantly criticises me in emails copied to the whole department. I am the intern so I feel I can't say anything.”
- D27: expected **high**, got medium (no warning words). “Julia Walsh was pushed against a wall by a visitor in reception and nobody intervened. She is too scared to report it herself.”
- D34: expected **medium**, got low (no warning words). “Laura Haddad told me to sign off a safety inspection that never happened. Her email is l.haddad@company.example.”
- D35: expected **high**, got low (no warning words). “I don't know where else to say this. Things at work have got so bad that I've had thoughts of ending my life.”
- D41: expected **medium**, got low (no warning words). “Someone in finance is taking a cut from supplier payments. Contact nadia at company dot com, she knows more.”
- D42: expected **medium**, got low (no warning words). “Efe Okafor's team leader screams at people when targets are missed. Efe is too afraid to speak up.”
- D48: expected **medium**, got low (no warning words). “I'm the newest member of the design team and Hannah Dubois keeps telling me I'm stupid in front of everyone.”
- D49: expected **medium**, got low (no warning words). “Timesheets for the night team are being padded. Priya Fischer and Mo Manager both signed them off.”
