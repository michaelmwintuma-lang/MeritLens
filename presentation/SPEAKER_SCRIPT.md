# MeritLens: speaker script

The full talk in plain words, slide by slide. It is the same text as the speaker notes in
`MeritLens_Presentation.pptx`, so you can rehearse from either. Lines in (brackets) are reminders or technical
terms to give only if someone asks.

Total: about 20 to 25 minutes, then questions.

---

## The talk

### 1. MeritLens (title)  ·  about ½ min

Good morning. My project is called MeritLens.

In one line: it helps a company decide who is ready for promotion, explains every decision in plain words, and lets every employee answer back.

You don't need any background in computers or statistics to follow this talk. Whenever I use a technical idea, I'll explain it with an everyday comparison.

(Say your name and your supervisor's name here.)

### 2. Promotions often feel like a black box  ·  about 1½ min

Let's start with the problem. Think about how promotions usually work.

First, people hear "yes" or "no" but rarely "why", so they don't know what to improve.

Second, decisions copy the past. In the records this project learned from, 33 out of every 100 engineers were promoted, but only 2 out of every 100 support staff. If we simply copied those old decisions, a support worker would be held back just because of their department, not their work.

Third, if your record has a mistake, or you think the reasoning is unfair, there's usually no proper channel to say so.

MeritLens is designed to fix all three.

### 3. MeritLens in one sentence  ·  about 1 min

If you remember one thing from today, make it this sentence: the computer advises, people decide, and every employee can answer back.

The system works in three steps.

Predict: it gives each employee a readiness score, a bit like a weather forecast. A forecast says "70% chance of rain"; this says how likely someone's record looks like the records of people who were promoted.

Explain: every score comes with reasons in everyday language, and a list of realistic things that would raise it.

Respond: the employee can say whether the explanation made sense, or point out a mistake in their record.

The next slides go through each step.

### 4. Six people, six jobs  ·  about 1 min

Six kinds of people use MeritLens, and each one can only do their own job. The system checks this on every single request, not just by hiding buttons.

The employee sees their own score and reasons, and can answer back.
The manager recommends people from their team.
HR makes the final decision.
Finance confirms the pay rise. They never see the scores, only what they need to approve the cost.
The admin runs the accounts.
And an auditor can check every decision afterwards, but can't change anything.

Splitting the work like this means no single person can push a promotion through alone.

### 5. Step 1 · Predict  ·  about ¼ min

Step one: predict. How does a computer estimate whether someone is ready for promotion?

### 6. It learned from 100,000 past cases  ·  about 1 min

How does it learn? Imagine an experienced HR reviewer who has looked at a hundred thousand past cases. Over time they notice patterns: people with strong, improving performance and good project records tend to get promoted.

The model does the same thing, but with two big differences. It's consistent: the same record always gets the same score. And it writes down exactly how much each fact counts, so it can always explain why.

It looks at 20 facts about each person's work. In the past data, about 1 in 10 people had been promoted.

Important: all of this data is simulated. It comes from a free public dataset, so no real person's information was used.

(If asked: the "model" is an Explainable Boosting Machine, a type chosen because it can always show its reasoning.)

### 7. It looks at work, never at who you are  ·  about 1½ min

This is one of the most important design choices.

On the left: what the model is allowed to use. Only facts about someone's work: their performance, how they're developing, how reliable they are, and where they are in their career.

On the right: what it never sees. Gender, age, education and marital status, obviously. But also department, because otherwise the support worker from earlier would be marked down just for their team. Pay, because that could copy old pay gaps. And working hours, because we want to reward results, not just staying late.

Each of these exclusions has a written reason in the code.

### 8. It never punishes improvement  ·  about 1½ min

How did I choose which model to use? I trained four different kinds and gave them a common-sense test.

I took 2,000 people and improved their record a little: a bit more training, slightly better peer feedback, one more project. A sensible system should never give a lower score to someone who just got better.

The chart shows what happened. The popular models on top sometimes did exactly that: up to 30% of the time, an improvement made the score worse. That would be impossible to explain to an employee: "You did more training, so your chance went down."

Only the model at the bottom, the Explainable Boosting Machine, never did it, because it's built with that rule. Its accuracy was as good as the others, so it was the clear choice.

### 9. How good are its forecasts?  ·  about 1½ min

How good is it? I tested it once, on 20,000 records it had never seen before, so it couldn't have memorised the answers.

Here are three plain ways to put the results.

One: show it two people, one who was promoted and one who wasn't. 88 times out of 100, it gives the promoted person the higher score.

Two: of everyone who really was promoted, it finds about 6 in 10. It misses some, which is exactly why a human always makes the final decision.

Three: its percentages are honest. When it says 30%, about 30 in 100 of those people were in fact promoted. That's called being well calibrated.

So think of it like a good weather forecast: useful, but not perfect, and never the final word.

(Technical terms if asked: ROC-AUC 0.883, recall 59.5%, precision 41%, calibration error 0.006.)

### 10. Fair across groups  ·  about 1 min

But being accurate isn't enough; it also has to be fair.

I used a standard test from employment law called the four-fifths rule. It says: whichever group is recommended most, every other group should be recommended at least four-fifths, that's 80%, as often.

A score of 1.0 would mean perfectly equal. Gender scores 0.98, age 0.96, education 0.89. All comfortably above the 0.8 line.

Two more safeguards. First, any model that fails this test is blocked automatically and can never be switched on. Second, HR can see the same test on live decisions, at three stages: what the model recommends, who managers nominate, and who HR approves. So if unfairness creeps in through people, not just the computer, it shows up.

### 11. Step 2 · Explain  ·  about ¼ min

Step two: explain. A score on its own isn't much use. People need to know why, and what to do next.

### 12. Every score comes with reasons  ·  about 1½ min

This is the employee's own page, called "My growth". This is a demo employee called Eli.

At the top is the readiness score, shown against the line where the model would recommend promotion: 23%.

Next to it, in plain words: what this means, written like a person would say it.

Below that, what raised and lowered the score. Teal bars helped, orange bars held it back, and the longer the bar, the bigger the effect. For Eli, attendance helped, but a drop in performance since last year held them back the most.

These numbers aren't guesses about what the model was "thinking". Because of the type of model chosen, the contributions add up exactly to the score. And there's a "technical details" section with the exact numbers and a second, independent method (called LIME) for anyone who wants to double-check.

### 13. A path forward, and room to explore  ·  about 1½ min

Telling someone their score is low isn't enough. They need to know what to do about it.

On the left, "Your path to promotion": the smallest realistic improvements that would get them over the line. Realistic means no bigger than a typical step, and never beyond what the top 5% of employees achieve. Each suggestion has been tried on the model to make sure it really works. For 98 of the 108 demo employees not yet recommended, the system found a path. The employee can turn these tips into goals with their manager in a development plan.

On the right, "What if?": the employee can move sliders and watch the score change, like a savings calculator. Only things a person can actually work on are offered (you can't change your department or how long you've been in your role), and nothing is saved.

### 14. Step 3 · Respond  ·  about ¼ min

Step three, and this is what makes the project different from most: respond. The employee gets a voice.

### 15. Employees can answer back  ·  about 1½ min

Right under their explanation, every employee has two options.

The first is "Rate this explanation": was it clear, was it useful, and does any factor seem wrong or unfair? This tells HR how well the explanations are working. To protect privacy, HR only sees totals, and only once at least 5 people have answered. Managers never see them at all.

The second is "Correct my record". Say Eli's record shows 5 projects but they actually completed 8. They can ask HR to fix it and attach evidence, like a PDF or a photo. HR checks it. If HR confirms it, the record is corrected, Eli is re-scored, and every detail is logged: who changed what, the old and new value, and the score before and after. If HR rejects it, Eli gets the reason.

### 16. Feedback never moves a score  ·  about 1½ min

An obvious worry: if people can complain, will complaining raise their score? The answer is no, and this is built into the design.

On the left: a rating or a complaint never reaches the model. It's used to improve the explanations and to show HR where people disagree, but it can't move anyone's score, up or down.

On the right: the only thing that changes a record is a fact that HR has checked against evidence.

And it's not just a promise. There's an automatic test that records every score, then adds ratings, complaints and corrections, and checks that every score is still identical. Two more checks make sure the scoring part of the code can't even read the feedback.

One more detail: if someone is up for promotion while their correction is still pending, HR's screen warns them, and the decision can be held until the correction is settled. So nobody gets judged on a record that might be wrong.

### 17. People make every decision  ·  about 1½ min

Now let's follow one promotion from start to finish, to show that people make every decision.

First the model advises: a score and the reasons.

Then the manager recommends. They fill in a structured form, rating four areas from 1 to 5, each with a real example. If they disagree with the model, they must write down why.

Then HR decides. The system saves the model's view right next to HR's decision, so later anyone can see where people and the computer disagreed.

Then Finance signs off the pay rise, or sends it back with a reason.

And only when all of that is final is the employee told. Nobody hears about a promotion that might still change.

Pay rises have limits set by HR, salaries are never stored, and Finance only sees what they need.

### 18. Built to be trusted  ·  about 1 min

For a system like this to be used in a real company, people have to trust it. Six features are there for that.

One: every decision goes into a log where each entry is sealed to the one before it, like links in a chain. If anyone edits or deletes an old entry, the chain breaks, and one click shows it.

Two: a new version of the model only goes live when a named HR person has read its report card and switched it on. A model that failed the fairness test can never be switched on.

Three: fairness is checked on real decisions as they happen, not just once in the lab.

Four: privacy. Anyone can download everything held about them, people who leave can have their personal data erased, and old data is deleted automatically.

Five: secure sign-in, with two-step codes and lock-out after wrong passwords.

And six: optionally, big changes need a second HR person to approve them.

### 19. Works on any screen  ·  about ½ min

Employees won't always be at a desk, so MeritLens works on phones, tablets and computers, in light and dark themes. Here are three screens on a phone: signing in, a manager's overview, and the employee's growth page in dark mode.

All 45 pages were checked automatically for all six roles. There were zero accessibility problems against the international standard, WCAG, which covers things like screen readers, colour contrast and keyboard use. And every page was tested at phone widths from the smallest Androids up to the largest iPhones, so nothing overlaps or runs off the screen.

### 20. How we know it works  ·  about 1 min

How do I know it works? Four pieces of evidence.

400 automated tests check everything from who can see what, to the pay rules, to the privacy features. They all pass, on two different kinds of database.

The model was measured once, on 20,000 records it had never seen.

The isolation test showed that feedback changed exactly zero scores.

And with 5,000 employees loaded, even the slowest page loaded in about a quarter of a second.

The next step is a study with real people. Everything for it is ready inside the app: 11 tasks, a standard usability questionnaire, and questions about whether the process feels fair.

### 21. What it can't do yet  ·  about 1 min

It's important to be honest about the limits.

The data is simulated. A real company would need to retrain the model on its own promotion history, with consent.

It hasn't been tried with real staff yet; that's the study I just mentioned.

Fairness has a price. An earlier version that used department was more accurate at predicting past decisions, but only because it copied the old habit of promoting some departments more. I chose fairness over that kind of accuracy on purpose.

And it's ready to go live on a secure server, but it hasn't been run for real yet.

Future work: run the study, add a confidential way to report unfair treatment, and make sure department can't sneak back in through other measures.

### 22. Thank you  ·  about ½ min

To sum up: MeritLens predicts how ready someone is for promotion using only their work, explains every score in plain words with a realistic path forward, and gives every employee a way to answer back, while people make every decision and every step is recorded.

The computer advises. People decide. Everyone can answer back.

Thank you. I'm happy to take questions, or to show the live system.

---

## Glossary: technical words in plain English

| Word | Say this instead |
|---|---|
| Machine learning / model | A computer program that learns patterns from many past examples, like an experienced reviewer who has seen 100,000 cases |
| Readiness score / prediction | A forecast of how closely someone's record matches the records of people who were promoted, like a weather forecast's "chance of rain" |
| Threshold (23%) | The line above which the system would recommend promotion |
| Training data | The past examples it learned from (here: 100,000 simulated employee records) |
| Test set | Records kept aside and never shown to it while learning, used once to check how good it really is, like an exam it hasn't seen |
| Explainable Boosting Machine (EBM) | The kind of model chosen: it adds up one simple effect per fact, so it can always show exactly why it gave a score |
| Monotonic | "Never punishes improvement": getting better at something can never lower the score |
| Feature / input | One fact about a person's work, such as attendance or projects completed |
| ROC-AUC 0.883 | Shown one promoted and one non-promoted person, it ranks them the right way round 88 times in 100 |
| Recall 59.5% | Of the people who really were promoted, it spots about 6 in 10 |
| Precision 41% | Of the people it flags, about 4 in 10 were actually promoted: it is a prompt for a closer look, not a verdict |
| Calibration | Its percentages are honest: a 30% score means about 30 in 100 such people were promoted |
| Four-fifths rule | A fairness test from employment practice: every group should be recommended at least 80% as often as the most-recommended group |
| LIME | A second, independent method that double-checks the explanation |
| Audit trail (hash-chained) | A record of every decision where each entry is sealed to the one before, like links in a chain: change one and the chain breaks |
| Human in the loop | People make every decision; the computer only advises |
| Synthetic data | Simulated records, so no real person's information was used |

---

## Likely questions, with short answers

**"So does the computer decide who gets promoted?"**
No. It only advises. A manager recommends, HR decides, and Finance confirms the pay rise. If a manager disagrees
with the computer, they write down why, and HR's decision is saved next to the computer's view.

**"Can the system be biased against women, older staff, or certain groups?"**
It never sees gender, age, education, marital status or department. It was tested with the four-fifths rule and
passed for every group (0.98, 0.96 and 0.89, all above 0.8). A model that fails is blocked automatically, and the
same test runs on real decisions, including the managers' and HR's, so bias from people shows up too.

**"Why not use department? Isn't that useful information?"**
In the past data, engineers were promoted 16 times as often as support staff. Using department would make the
system copy that habit: two people with the same record would score differently just because of their team.
Leaving it out made the system less good at copying past decisions, and that is the point.

**"It only finds 6 in 10 promoted people. Isn't that bad?"**
It's a forecast, not a judge. Its job is to point out people worth a closer look and explain why; people make the
decision. Being honest about how accurate it is matters more than looking perfect.

**"If I complain, will my score go up?"**
No. Ratings and complaints never reach the model; an automatic test proves every score stays exactly the same.
Only a fact HR has checked against evidence can change a record.

**"What stops HR from quietly changing a decision later?"**
Every decision goes into the audit trail, where entries are chained together. If anyone edits or deletes an old
entry, the chain breaks, and one click shows it. An auditor can check it at any time.

**"Who can see my feedback?"**
HR and the auditor see only totals, and only when at least 5 people have answered. Your manager never sees it.

**"Was real employee data used?"**
No. All 100,000 records are simulated, from a free public dataset on Kaggle.

**"Could a real company use it tomorrow?"**
Not quite: it would need to learn from that company's own promotion history (with consent), and the study with
real users still has to be run. The secure server set-up is written and ready.

**"What would you add next?"**
Run the user study; add a confidential way to report unfair treatment; and make sure department can't sneak back in
through other measures, such as how many projects are typical in each team.
