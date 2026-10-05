"""
Anonymiser: removes details that could identify people from a report, before anything is saved.

- Names of people in the employee directory become [PERSON 1], [PERSON 2], ... (the same person keeps the same tag).
- Email addresses become [EMAIL 1], phone numbers [PHONE 1], dates [DATE 1].
- Phrases that could point to the reporter ("I'm the only woman in my team") are not removed, because the
  reporter may need them, but they are flagged as a warning so the reporter can decide.

It works with simple, readable rules (regular expressions and a name list). That makes it predictable and easy to
check, but it only catches what the rules describe: the reporter always reviews and approves the result.
"""
import re

EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
# 7 or more digits, optionally with spaces, dashes, dots, brackets or a leading +
PHONE = re.compile(r"(?<![\w-])\+?\(?\d[\d\s().-]{5,}\d(?![\w-])")
MONTHS = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
DATE = re.compile(
    r"\b(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}"                      # 12/03/2025, 12-03-25
    r"|\d{4}-\d{1,2}-\d{1,2}"                                     # 2025-03-12
    rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{MONTHS}(?:\s+\d{{4}})?"   # 12 March, 3rd of May 2025
    rf"|{MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?)\b",       # March 12, May 3rd 2025
    re.IGNORECASE,
)

# Phrases that could narrow down who the reporter is, and why
IDENTIFYING_PHRASES = [
    (r"\b(?:i'?m|i am|as) the only\b[^.,;!?]*", "Saying you are the only one of something can identify you."),
    (r"\bthe only (?:woman|man|female|male|person|one|black|white|asian|muslim|christian|jewish|disabled)\b[^.,;!?]*", "Being the only one of a group can identify you."),
    (r"\b(?:i'?m|i am|i was) (?:the )?(?:new|youngest|oldest|newest|most senior|most junior)\b[^.,;!?]*", "Your position in the team can identify you."),
    (r"\b(?:i'?ve|i have) (?:worked|been) here (?:for )?\d+\s+(?:years?|months?)\b", "How long you've worked here can identify you."),
    (r"\b(?:since|when) i (?:joined|started)\b[^.,;!?]*", "When you joined can identify you."),
    (r"\bmy (?:desk|office|seat|shift|wife|husband|partner|child|children|son|daughter|pregnancy|religion|disability)\b", "Personal details can identify you."),
    (r"\b(?:i'?m|i am) (?:pregnant|disabled|a single (?:mum|mom|dad|parent))\b", "Personal circumstances can identify you."),
    (r"\b(?:i'?m|i am) the (?:team lead|lead|supervisor|intern|apprentice|assistant)\b[^.,;!?]*", "Your job title can identify you."),
]
IDENTIFYING = [(re.compile(pattern, re.IGNORECASE), reason) for pattern, reason in IDENTIFYING_PHRASES]


def _name_pattern(name: str, any_case: bool = True) -> re.Pattern:
    """Whole-word match for a name; case-insensitive unless any_case is False."""
    return re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE if any_case else 0)


def anonymise(text: str, directory_names: list[str]) -> dict:
    """
    Return the cleaned text, what was replaced (shown only to the reporter, never stored), and warnings.
    `directory_names` are the full names of people in the organisation.
    """
    replaced = []
    counters = {}
    person_tags = {}  # lower-case full name -> its tag, so first or last names alone reuse it

    def tag_for(kind: str) -> str:
        counters[kind] = counters.get(kind, 0) + 1
        return f"[{kind} {counters[kind]}]"

    def person_tag(key: str) -> str:
        """The person's tag, created the first time they appear."""
        if key not in person_tags:
            person_tags[key] = tag_for("PERSON")
        return person_tags[key]

    # 1. Emails and phone numbers first, so their digits and names aren't half-replaced later
    for kind, pattern in (("EMAIL", EMAIL), ("PHONE", PHONE)):
        def swap(match, kind=kind):
            tag = tag_for(kind)
            replaced.append({"original": match.group(0), "tag": tag, "type": kind.lower()})
            return tag
        text = pattern.sub(swap, text)

    # 2. Dates
    def swap_date(match):
        tag = tag_for("DATE")
        replaced.append({"original": match.group(0), "tag": tag, "type": "date"})
        return tag
    text = DATE.sub(swap_date, text)

    # 3. Full names from the directory, longest first so "Ann Lee-Smith" wins over "Ann Lee"
    for name in sorted(set(directory_names), key=len, reverse=True):
        pattern = _name_pattern(name)
        if pattern.search(text):
            tag = person_tag(name.lower())
            text = pattern.sub(tag, text)
            replaced.append({"original": name, "tag": tag, "type": "name"})

    # 4. First or last names on their own, if they belong to someone in the directory. Only when capitalised,
    #    as names are written: many surnames are also ordinary words ("Brooks", "Rose", "Manager").
    parts = {}
    for name in directory_names:
        for part in name.split():
            if len(part) > 2:
                parts.setdefault(part, []).append(name.lower())
    for part, owners in sorted(parts.items(), key=lambda kv: len(kv[0]), reverse=True):
        pattern = _name_pattern(part, any_case=False)
        match = pattern.search(text)
        if not match:
            continue
        # Reuse the tag of a person already named in full in this report, otherwise give a new one
        known = next((person_tags[o] for o in owners if o in person_tags), None)
        tag = known or person_tag(f"part:{part.lower()}")
        replaced.append({"original": match.group(0), "tag": tag, "type": "name"})
        text = pattern.sub(tag, text)

    # 5. Number the tags in the order they appear, so the text reads naturally ([PERSON 1] comes first)
    text, replaced = _renumber(text, replaced)

    # 6. Warnings: phrases that stay in the text but could identify the reporter
    # (one warning per stretch of text: a phrase matched by two rules is reported once)
    warnings, taken = [], []
    for pattern, reason in IDENTIFYING:
        for match in pattern.finditer(text):
            start, end = match.span()
            if any(start < t_end and t_start < end for t_start, t_end in taken):
                continue
            taken.append((start, end))
            warnings.append({"phrase": match.group(0).strip(), "reason": reason})

    return {"text": text, "replaced": replaced, "warnings": warnings}


TAG = re.compile(r"\[(PERSON|EMAIL|PHONE|DATE) (\d+)\]")


def _renumber(text: str, replaced: list[dict]) -> tuple[str, list[dict]]:
    """Renumber each kind of tag by first appearance: the first person mentioned becomes [PERSON 1]."""
    new_numbers, counts = {}, {}
    for kind, number in TAG.findall(text):
        if (kind, number) not in new_numbers:
            counts[kind] = counts.get(kind, 0) + 1
            new_numbers[(kind, number)] = counts[kind]

    def swap(match):
        return f"[{match.group(1)} {new_numbers[(match.group(1), match.group(2))]}]"
    return TAG.sub(swap, text), [{**r, "tag": TAG.sub(swap, r["tag"])} for r in replaced]


def still_identifying(text: str, directory_names: list[str]) -> list[str]:
    """What the anonymiser would still replace in an edited text (empty if it's clean)."""
    return [r["original"] for r in anonymise(text, directory_names)["replaced"]]
