"""
Triage: how urgent is a report? High, medium (shown as "Moderate") or low.

1. The language model reads the report and suggests a level (app/reporting/priority_model.py). It understands
   more than a word list: it learns from examples, so a threat or an unwanted touch described without any
   alarming word can still read as high, and figures of speech like "smashed our targets" read as harmless.
2. Safety net: the model can be wrong, and putting an urgent report too low is the costly mistake, so two rules
   can raise (never lower) its suggestion:
   - words that clearly suggest danger ("knife", "assaulted", "suicide") or a risk of self-harm ("end my life",
     "no point in going on") mean at least high. Harmless phrases that
     only look alarming ("hit our targets", "killing it") are ignored;
   - some categories have a minimum: safety reports are always at least high, harassment and discrimination at
     least medium (both from the brief); sexual harassment or assault, violence, and risk of self-harm are
     always high; retaliation and drug or alcohol misuse at least medium.
3. The reasons are returned in plain words, with the words that drove the model, so HR can see why. HR can
   always change the priority.
"""
import re

from app.reporting import priority_model

HIGH = ["threaten", "threatened", "threatening", "threat", "unsafe", "danger", "dangerous", "hit me", "hits me",
        "punched", "kicked", "slapped", "pushed me", "assault", "assaulted", "attacked me", "weapon", "knife", "gun",
        "kill", "hurt me", "injured", "violence", "violent", "sexual", "groped", "grabbed me", "stalking", "stalked",
        "suicide", "self-harm", "fire exit blocked", "blocked fire exit", "gas leak"]
# Risk of self-harm is never left to the model alone: these phrases always mean high. (Added after the developer
# evaluation set had been seen, so they flatter its one self-harm report: see docs/EVALUATION.md.)
SELF_HARM = ["kill myself", "killing myself", "end my life", "ending my life", "take my own life", "taking my own life",
             "end it all", "ending it all", "ending things", "end things", "hurt myself", "hurting myself", "harm myself",
             "want to die", "wish i was dead", "wish i were dead", "better off without me", "no reason to live",
             "no point in living", "no point in going on", "don't want to be alive", "do not want to be alive",
             "don't want to live", "suicidal", "overdose"]
# Everyday phrases that contain alarming words but aren't
HARMLESS = ["hit our target", "hit our targets", "hit the target", "hit the targets", "hit the deadline",
            "hit the ground running", "hit it off", "killing it", "killed it", "kill two birds", "deadline is killing",
            "kill time", "attack the problem", "threat of rain", "dangerously close to the deadline"]
CATEGORY_MINIMUM = {"safety": "high", "harassment": "medium", "discrimination": "medium",
                    "sexual_harassment": "high", "violence": "high", "harm_risk": "high",
                    "retaliation": "medium", "substance": "medium"}
LEVELS = priority_model.LEVELS
LABELS = {"low": "low", "medium": "moderate", "high": "high"}


def _find(words: list[str], text: str) -> list[str]:
    """Which of these words or phrases appear (as whole words, any capitalisation)."""
    return [w for w in words if re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE)]


def danger_words(text: str) -> list[str]:
    """Words suggesting danger, ignoring harmless phrases that only look alarming."""
    cleaned = text
    for phrase in HARMLESS:
        cleaned = re.sub(rf"\b{re.escape(phrase)}\b", " ", cleaned, flags=re.IGNORECASE)
    return _find(HIGH + SELF_HARM, cleaned)


def triage(text: str, category: str) -> dict:
    """The suggested priority, the model's reading, the words to mark in the text, and the reasons in plain words."""
    reading = priority_model.predict(text)
    level = reading["priority"]
    words = ", ".join(f"“{w['word']}”" for w in reading["words"])
    reasons = [f"The language model read this as {LABELS[level]} priority ({round(reading['confidence'] * 100)}% sure)"
               + (f", mainly because of {words}." if words else ".")]

    danger = danger_words(text)
    if danger and level != "high":
        level = "high"
        reasons.append(f"Raised to high by the safety rules: words suggesting danger ({', '.join(danger)}).")
    minimum = CATEGORY_MINIMUM.get(category)
    if minimum and LEVELS.index(minimum) > LEVELS.index(level):
        level = minimum
        reasons.append(f"Raised to {LABELS[minimum]}: reports in this category are always at least {LABELS[minimum]} priority.")

    # Words to mark in the text: danger words, then the words that drove the model (unless it read the report as low)
    triggers = [{"word": w, "level": "high"} for w in danger]
    if reading["priority"] != "low":
        seen = {d.lower() for d in danger}
        triggers += [{"word": w["word"], "level": reading["priority"]} for w in reading["words"] if w["word"] not in seen]
    return {"priority": level, "triggers": triggers, "reasons": reasons, "model": reading}
