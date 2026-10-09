# User test: how to run it

A short test with real people shows whether the platform is usable and whether the explanations build
understanding and trust. Plan about 30 minutes per person, with 5 to 8 people (5 is enough to find most usability
problems; more gives steadier numbers).

> **Ethics first.** Most universities require approval before any study with people, even a small, anonymous one.
> Check with your supervisor before you start. Participants must never report real misconduct: they use the
> made-up scenarios below.

## Before each session

- Start the app (`python run.py`) on a computer you control. Use the demo accounts (`employee`, `manager`, `hr`
  with `demo1234`), so no personal data is involved.
- Read the consent note below to the participant and make sure they agree.
- Give each person a code (P1, P2, ...). Never write their name next to their answers.

### Consent note (read aloud)

> "This is a test of a student project, not a test of you. You'll try a few tasks on a website using made-up data,
> then answer a short questionnaire. Please think aloud as you go. I'll note whether each task was completed and
> roughly how long it took. Your answers are anonymous and only used in my final-year project. You can stop at any
> time without giving a reason. Is that OK?"

## Tasks

Read each task aloud; don't explain how to do it. Note **yes** (completed alone), **help** (completed after a
hint) or **no**, and the time in seconds.

| # | Sign in as | Task |
|---|---|---|
| T1 | employee | "Find your readiness score and say, in your own words, the main thing holding it back." |
| T2 | employee | "Find out what would happen to your score if your training hours went up." |
| T3 | employee | "You saw a colleague being shouted at. Report it anonymously, and keep what you need to check for a reply later." *(Give them this scenario card: "In the meeting on 3rd of May, Nadia Varga shouted at a new team member and called them useless.")* |
| T4 | hr | "Find the report that was just sent and reply to the reporter asking for more detail." |
| T5 | employee | "Check whether HR has replied to your report." |
| T6 | manager | "Nominate the team member with the highest readiness for promotion, with a reason." |
| T7 | hr | "Decide on that nomination. Suppose you disagree with the model: record your decision." |
| T8 | employee | "Tell the system whether the explanation of your score was clear and useful, and mark any factor that seems unfair to you." |
| T9 | employee | "Your record says you completed fewer projects than you did. Ask HR to correct it." *(Scenario card: "Your signed review form from March lists 3 more completed projects than the record shows.")* |
| T10 | employee | "You believe your last appraisal was biased. Raise this anonymously." *(Scenario card: "Your manager rated you lower than colleagues who did less, and said it was because you 'don't fit in'.")* |
| T11 | hr | "An employee has asked for a record correction. Check it and decide." |

T8 to T11 cover the employee feedback channel: the three ways to respond to an explanation (rate it, ask for a
correction, report anonymously), and HR acting on a correction.

Afterwards, tidy up what the test created: as HR, close the made-up cases. To start every session from the same
state, copy `backend/instance/app.db` somewhere safe before the first session and copy it back after each one
(with the app stopped). Deleting `app.db` also works, but it recreates only the demo data: accounts, employees
and passwords you've changed or added yourself would be lost.

## Questionnaire

Answer each statement from 1 (strongly disagree) to 5 (strongly agree).

**System Usability Scale** (Brooke, 1996; keep the wording and order exactly as below):

1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.

**About this platform** (scored separately, not part of SUS):

- e1. The explanations helped me understand why a readiness score was what it was.
- e2. I would trust a promotion decision made with this system's advice.
- e3. When reporting, I felt my identity was protected.
- e4. I could find what I needed without help.

**Perceived fairness** (adapted from Colquitt, 2001; scored separately, not part of SUS). Ask these after the
employee tasks, about the participant's own score and explanation:

*Informational fairness: the explanation*

- i1. The system explained the reasons for my readiness score clearly.
- i2. The system's explanation of my readiness score was reasonable.
- i3. The system explained how my readiness score was worked out thoroughly.
- i4. The explanation was tailored to my own situation.

*Procedural fairness: the process*

- p1. I was able to express my views about the assessment.
- p2. I could ask for a wrong record to be corrected.
- p3. The assessment was based on accurate information.
- p4. The assessment was free of bias.

Colquitt's original items ask about a decision-maker ("Has he/she explained the procedures thoroughly?"; "Have you
been able to express your views?"). Here they are reworded as statements about the system, on the same 1 to 5
scale as the rest of the questionnaire. Say so when reporting the results.

Finally ask: *"What was the most confusing moment, and what would you change?"* and note the answer.

## Recording and scoring

Fill in two files in `backend/evaluation/`:

- `user_test_sus.csv`: one row per participant:
  `participant, role_played, q1 ... q10, e1 ... e4, i1 ... i4, p1 ... p4, comments`
  (e.g. `P1, employee and hr, 4, 2, 4, 1, 4, 2, 5, 2, 4, 2, 5, 4, 4, 4, 5, 4, 4, 3, 4, 5, 4, 3, "Didn't see the key download at first"`).
- `user_test_tasks.csv`: one row per participant per task: `participant, task, completed, seconds, notes`, with
  `completed` as yes, help or no (e.g. `P1, T3, help, 140, looked for the menu`).

Then, from the `backend` folder:

```
python -m evaluation.user_test
```

This writes `results/user_test.md`: the mean SUS score (68 is the published average; above it is better than
average), each person's score and grade, the answers to e1 to e4, the two fairness scales (each person's mean over
the four statements, the group mean and, from three participants up, Cronbach's alpha), task completion and times,
and the comments.
Report the numbers with the number of participants, and use the comments and failed tasks to explain them.
