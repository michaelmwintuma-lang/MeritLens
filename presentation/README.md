# Presenting MeritLens to people who don't know machine learning

This folder has everything for presenting the project:

| File | What it is |
|---|---|
| `MeritLens_Presentation.pptx` | The slide deck: 22 slides, about 20 to 25 minutes, with speaker notes on every slide (in PowerPoint: View → Notes) |
| `SPEAKER_SCRIPT.md` | The full talk in plain words, slide by slide, plus a glossary and answers to likely questions |
| `README.md` | This guide: how to approach the talk |

---

## The best approach: tell a story, not a list of features

People who don't know machine learning won't remember "an Explainable Boosting Machine with monotonic constraints".
They will remember a story with a problem, an idea, and a person it helps. So the talk follows one arc:

1. **The problem everyone recognises.** Promotions feel like a black box: no reasons, old habits repeat, no way to
   answer back. Start here because everyone in the room has an opinion about promotions.
2. **The idea in one sentence.** *"The computer advises, people decide, and every employee can answer back."*
   Say it early, repeat it at the end. If they remember nothing else, they remember this.
3. **Three steps: Predict, Explain, Respond.** Each step gets a dark divider slide, so the audience always knows
   where they are.
4. **Why you can trust it.** People decide every step; fairness is tested; nothing can be secretly changed.
5. **Honesty about the limits.** Saying what it can't do yet makes everything else more believable.

### Five rules for a non-technical audience

1. **Use an everyday comparison for every technical idea.** They're all in the script:
   - the model is like *an experienced reviewer who has seen 100,000 cases*;
   - the score is like *a weather forecast*: useful, sometimes wrong, never the final word;
   - the audit trail is like *links in a chain*: break one and it shows;
   - "what if?" is like *a savings calculator*.
2. **Turn numbers into people.** Say "88 times out of 100", not "ROC-AUC 0.883"; "about 6 in 10", not "recall
   59.5%". The technical terms are in the speaker notes if someone asks.
3. **Follow one person.** The demo employee, Eli, appears in the screenshots. Talk about what *Eli* sees and can do.
4. **Never say a word you haven't explained.** If you must say "model", "algorithm" or "fairness ratio", say what it
   means the first time (see the glossary in `SPEAKER_SCRIPT.md`).
5. **Show, don't tell, if you can.** A two-minute live demo beats five slides.

---

## Timing (about 20 to 25 minutes, plus questions)

| Part | Slides | Minutes |
|---|---|---|
| Opening: problem, one sentence, who uses it | 1–4 | 4 |
| Step 1 · Predict: how it learned, what it uses, how good and fair it is | 5–10 | 6 |
| Step 2 · Explain: reasons, path to promotion, what-if | 11–13 | 3 |
| Step 3 · Respond: answering back; feedback never moves a score | 14–16 | 3 |
| Trust: people decide, safeguards, any screen | 17–19 | 3 |
| Closing: evidence, limits, thank you | 20–22 | 2 |

Shorter version (10 minutes): skip slides 4, 6, 9, 18 and 19, and say one sentence about each instead.

---

## Adding a live demo (recommended, 2–4 minutes)

Do it after slide 16 ("Feedback never moves a score"), or at the very end if time is tight.

1. Before the talk, start the app (`python run.py` in the project folder) and open http://127.0.0.1:5173.
   The demo accounts and their shared password are in the main `README.md` under "Demo accounts".
2. **Sign in as `employee`** → *My growth*. Point out the score, the plain-words summary, and the teal and orange
   bars. Move one *What if?* slider and show the score change.
3. Scroll to **Respond to this explanation** and show the two buttons.
4. **Sign in as `hr`** → *Nominations* → open a nomination. Show the model's view next to the manager's
   recommendation, and the committee note if a correction is pending. If the list is empty, sign in as `manager`
   beforehand and recommend someone from *My team*, so there is one to show.
5. Back to the slides.

Rehearse it once. If anything goes wrong on the day, carry on with the screenshots: they show the same screens.

---

## Before the day

- Put your name and your supervisor's name on slide 1 (the speaker notes remind you).
- Read `SPEAKER_SCRIPT.md` aloud once with a timer.
- Read the "Likely questions" section at the end of the script: these are the questions non-experts usually ask.
- In PowerPoint, use **Presenter View** (Slide Show → Use Presenter View) so you see your notes and the audience
  doesn't.
