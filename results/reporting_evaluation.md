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

Triage is the language model, with safety rules that can only raise its suggestion (danger and self-harm words, and category minimums). The earlier keyword-only method is shown for comparison. *Under-triaged* = given a lower priority than needed, the costly mistake.

| Method | Accuracy | Under-triaged | Over-triaged |
|---|---|---|---|
| Keywords only (before) | 74% | 12 | 1 |
| Language model alone | 64% | 7 | 11 |
| **Language model + safety rules (used)** | **66%** | **5** | **12** |

Confusion matrix for the method used:

| Expected ↓ / Given → | Low | Medium | High | Recall |
|---|---|---|---|---|
| Low | 4 | 2 | 5 | 36% |
| Medium | 5 | 15 | 5 | 60% |
| High | 0 | 0 | 14 | 100% |
| **Precision** | 44% | 88% | 58% | |

**Mistakes** (with what the model said and the words that drove it):

- D02: expected **medium**, got high (model: high, 54% sure; happened, month, floor). “Nadia shouted at me in front of the whole Sales floor and called me useless. It has happened three times this month.”
- D06: expected **medium**, got low (model: low, 45% sure; no marked words). “I believe Samuel Varga is approving his own expense claims. You can check invoice 20250114 and ticket 4471229 in the system.”
- D11: expected **medium**, got low (model: low, 58% sure; no marked words). “My manager asked me to change the delivery dates on the client report so we hit our targets for the quarter. I think this is fraud.”
- D12: expected **low**, got high (model: low, 88% sure; kill). “The new product launch is going to kill the competition, but the marketing team is working until midnight every day and people are exhausted.”
- D16: expected **medium**, got low (model: low, 42% sure; no marked words). “A supplier contact, Derek Holt, offered me a holiday if we chose his company. I said no but I think others accepted a bribe.”
- D21: expected **low**, got medium (model: medium, 34% sure; told, shifts). “I was told to raise this with the Manager on duty but they never answer. The rota for Saturday shifts is unfair.”
- D23: expected **medium**, got high (model: high, 39% sure; told, racist, witnesses). “Racist jokes are told at lunch by Hannah Castillo and William Mensah. Call me on +44 20 7946 0958 if you need witnesses.”
- D24: expected **medium**, got high (model: high, 74% sure; night, switched, store, going). “Stock is going missing from the store room and I think someone is stealing it at night. The CCTV was switched off on March 14.”
- D25: expected **low**, got high (model: high, 50% sure; security, patched). “Our software is still on version 3.14.207 and the security team has not patched it. This is an Admin team issue, not IT.”
- D26: expected **medium**, got low (model: low, 44% sure; no marked words). “Ibrahim Walsh constantly criticises me in emails copied to the whole department. I am the intern so I feel I can't say anything.”
- D29: expected **medium**, got high (model: high, 40% sure; night, shift, break). “During Ramadan my requests to move my break were refused, while others get flexibility. I'm the only Muslim on the night shift.”
- D32: expected **low**, got high (model: high, 39% sure; no marked words). “The training budget was cut but managers still went on an expensive retreat. It does not seem fair, but I'm not sure it breaks any rule.”
- D33: expected **medium**, got high (model: high, 52% sure; said, partner, works). “Oliver Rossi keeps asking me out even though I've said no several times. My partner also works here and it is very awkward.”
- D39: expected **low**, got medium (model: medium, 39% sure; demotivating, goes). “The Employee of the Month award always goes to the same three people. It is demotivating for everyone else.”
- D42: expected **medium**, got low (model: low, 48% sure; no marked words). “Efe Okafor's team leader screams at people when targets are missed. Efe is too afraid to speak up.”
- D46: expected **low**, got high (model: high, 42% sure; guard, security, visitors). “Brooks the security guard is very rude to visitors at the front desk, which gives a bad impression.”
- D50: expected **low**, got high (model: high, 40% sure; machine, broken, called). “The coffee machine has been broken since 0771-234-567 was called for repair; nobody follows up. I sit by the window so I hear all the complaints.”
