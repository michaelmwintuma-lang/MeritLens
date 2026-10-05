"""
Simple triage: how urgent is a report? High, medium or low, from a keyword list.

1. Harmless phrases that only look alarming ("hit our targets", "killing it") are removed first.
2. Words that suggest danger ("threatened", "unsafe", "hit me") mean high; words that suggest mistreatment
   ("harassed", "bullied", "humiliated") mean medium; otherwise low.
3. Some categories have a minimum: safety reports are always at least high; harassment and discrimination at
   least medium.
4. The words that caused the priority are returned, so HR can see why. HR can always change the priority.
"""
import re

HIGH = ["threaten", "threatened", "threatening", "threat", "unsafe", "danger", "dangerous", "hit me", "hits me",
        "punched", "kicked", "slapped", "pushed me", "assault", "assaulted", "attacked me", "weapon", "knife", "gun",
        "kill", "hurt me", "injured", "violence", "violent", "sexual", "groped", "grabbed me", "stalking", "stalked",
        "suicide", "self-harm", "fire exit blocked", "blocked fire exit", "gas leak"]
MEDIUM = ["harass", "harassed", "harassing", "harassment", "discriminate", "discriminated", "discrimination",
          "bully", "bullied", "bullying", "intimidate", "intimidated", "intimidating", "humiliate", "humiliated",
          "shouted", "shouting", "screamed", "yelled", "insulted", "abusive", "abuse", "racist", "sexist", "slur",
          "excluded", "mocked", "mocking", "ridiculed", "belittled", "retaliate", "retaliated", "retaliation",
          "fraud", "bribe", "stole", "stealing"]
# Everyday phrases that contain alarming words but aren't
HARMLESS = ["hit our target", "hit our targets", "hit the target", "hit the targets", "hit the deadline",
            "hit the ground running", "hit it off", "killing it", "killed it", "kill two birds", "deadline is killing",
            "kill time", "attack the problem", "threat of rain", "dangerously close to the deadline"]
CATEGORY_MINIMUM = {"safety": "high", "harassment": "medium", "discrimination": "medium"}
LEVELS = ["low", "medium", "high"]


def _find(words: list[str], text: str) -> list[str]:
    """Which of these words or phrases appear (as whole words, any capitalisation)."""
    return [w for w in words if re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE)]


def triage(text: str, category: str) -> dict:
    """The suggested priority, the words that triggered it, and the reasons in plain words."""
    cleaned = text
    for phrase in HARMLESS:
        cleaned = re.sub(rf"\b{re.escape(phrase)}\b", " ", cleaned, flags=re.IGNORECASE)
    high, medium = _find(HIGH, cleaned), _find(MEDIUM, cleaned)
    level = "high" if high else "medium" if medium else "low"
    reasons = []
    if high:
        reasons.append(f"Words suggesting danger: {', '.join(high)}.")
    elif medium:
        reasons.append(f"Words suggesting mistreatment: {', '.join(medium)}.")
    else:
        reasons.append("No warning words found.")
    minimum = CATEGORY_MINIMUM.get(category)
    if minimum and LEVELS.index(minimum) > LEVELS.index(level):
        level = minimum
        reasons.append(f"{category.capitalize()} reports are always at least {minimum} priority.")
    return {"priority": level, "triggers": [{"word": w, "level": "high"} for w in high] +
            [{"word": w, "level": "medium"} for w in medium], "reasons": reasons}
