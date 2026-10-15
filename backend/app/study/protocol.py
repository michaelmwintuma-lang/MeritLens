"""
The user study's protocol, as in docs/USER_TEST.md: the consent note, the eleven tasks (in this order: T9 needs T5's
request, T11 needs T9's decision), and the questionnaire. The SUS wording and order are Brooke's (1996), unchanged;
the explanation and fairness statements come from evaluation/user_test.py, which scores them, so they are written
in one place.
"""
from evaluation.user_test import EXTRA, FAIRNESS

CONSENT = ("This is a test of a student project, not a test of you. You'll try a few tasks on a website using made-up "
           "data, then answer a short questionnaire. Please think aloud as you go. I'll note whether each task was "
           "completed and roughly how long it took. Your answers are anonymous and only used in my final-year project. "
           "You can stop at any time without giving a reason. Is that OK?")

TASKS = [
    ("T1", "employee", "Find your readiness score and say, in your own words, the main thing holding it back.", None),
    ("T2", "employee", "Find out what would happen to your score if your training hours went up.", None),
    ("T3", "employee", "Find your path to promotion and say which step you would start with.", None),
    ("T4", "employee", "Tell the system whether the explanation of your score was clear and useful, and mark any factor that seems unfair to you.", None),
    ("T5", "employee", "Your record says you completed fewer projects than you did. Ask HR to correct it.",
     "Scenario card: your signed review form from March lists 3 more completed projects than the record shows."),
    ("T6", "manager", "Nominate the team member with the highest readiness for promotion, with a reason.", None),
    ("T7", "manager", "Open a team member's explanation and say what most lowered their score.", None),
    ("T8", "hr", "Decide on that nomination. Suppose you disagree with the model: record your decision.", None),
    ("T9", "hr", "An employee has asked for a record correction. Check it and decide.", None),
    ("T10", "hr", "On the feedback dashboard, find which factor employees contest most.", None),
    ("T11", "employee", "Check whether HR has decided on your correction request.", None),
]

SUS = {
    "q1": "I think that I would like to use this system frequently.",
    "q2": "I found the system unnecessarily complex.",
    "q3": "I thought the system was easy to use.",
    "q4": "I think that I would need the support of a technical person to be able to use this system.",
    "q5": "I found the various functions in this system were well integrated.",
    "q6": "I thought there was too much inconsistency in this system.",
    "q7": "I would imagine that most people would learn to use this system very quickly.",
    "q8": "I found the system very cumbersome to use.",
    "q9": "I felt very confident using the system.",
    "q10": "I needed to learn a lot of things before I could get going with this system.",
}

# The questionnaire in the order it is asked: each section's heading and its statements
SECTIONS = [
    ("How easy it was to use (System Usability Scale)", SUS),
    ("About this platform", EXTRA),
    *[(f"{name}: about your own score and explanation", items) for name, items in FAIRNESS.items()],
]
ITEMS = [key for _, items in SECTIONS for key in items]
