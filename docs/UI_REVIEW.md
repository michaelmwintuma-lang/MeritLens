# UI review: MeritLens before and after the UI overhaul

Baseline: tag `before-ui-overhaul` (commit 5db091a). Work continues on branch `ui-overhaul`.

Screenshots: `docs/screenshots/before-ui/`, 39 pages for all six roles plus the public site. Each page was
captured at 1366 px (desktop) and 390 px (phone), with axe-core results in `axe.json`. They were taken with
`python scripts/browser_test.py scripts/ui_capture.js docs/screenshots/before-ui`, which runs against a throwaway
copy with the demo accounts. `ui_capture.js` now covers every route and seeds a small demo scenario: a nomination
on hold for a pending correction, and an approved pay rise waiting for Finance.

Automated baseline: **0 axe-core findings** on every page. **One page is wider than a phone:** the HR nomination
review is 541 px wide on a 390 px screen.

## 1. Problems that affect every page

**Typography**
- The font is the system stack (`-apple-system`, "SF Pro", Inter, Segoe UI), so it looks different on Windows,
  macOS and Android, and it isn't Montserrat.
- There's no type scale. The style sheets use **23 different font sizes** (11, 12, 12.5, 13, 13.5, 14, 14.5, 15,
  15.5, 16, 16.5, 17, 17.5, 18, 19, 20, 21, 22, 26, 28, 32, 34 and 44 px).
- Some body and helper text is 11 to 13 px, below the 14 px minimum. Examples: the hint under the readiness bar,
  "Now: 51.5" under each what-if slider, and the "lowers" labels.
- Dates and hyphenated words get stretched gaps: "2026 - 10 - 15", "Pay sign - off", "cross - department". This
  happens in titles, tables and the activity log and looks like a rendering bug.
- Numbers mostly don't use tabular figures, so scores, PSI values and KPI tiles don't line up in columns.
- Uppercase small labels like "OVERALL" and "WHY THE MANAGER DISAGREES…" don't use the same letter-spacing
  everywhere.

**Colour and identity**
- The interface is Apple blue (`#0071e3`) with a blue-to-violet gradient icon. The navy and teal identity was
  replaced in the last redesign (commit bcdd055). Navy now exists only as black "ink", and teal only as the
  "raises the score" data colour. See question 1 at the end.
- Colour tokens are spread out: there are 56 distinct hex values across `styles.css`, `login.css` and
  `public.css`, and the token names mix roles (`--navy` is actually near-black).
- Disabled primary buttons are pale blue on white and hard to read. Examples: "See the new score", "Save my
  rating", "Reject the request", "Clear filters". axe doesn't check disabled controls, but people still need to
  read them.

**Spacing, shape and depth**
- Spacing doesn't follow a grid. Card padding, gaps between cards and table cell padding all vary by page.
- Panels use a 20 px radius, fields 12 px, and buttons are fully rounded pills. The look is soft but
  inconsistent, and it doesn't match the 8 px and 6 px radii in the brief.
- Every page title has a large blue gradient icon tile next to it. That's visually loud, and the same icon is
  already in the sidebar.

**Components**
- There are 73 inline `style={{…}}` attributes across pages and components, which are one-off layout and colour
  fixes.
- Several patterns are rebuilt on each page instead of shared: stat tiles (Finance, Feedback, Admin), segmented
  tabs (Corrections, Finance, Respond panel), "label: value" rows, and the coloured left-border quote boxes.
- There's no loading skeleton. Loading shows a centred "Loading…" spinner, which fills a whole page when a page's
  code is fetched for the first time. The `hr-employees` desktop capture caught exactly that: a blank page with
  "Loading…".
- Empty states are mostly a grey sentence like "No factor has been marked yet." or "None signed off yet this
  year." There's a shared `EmptyState` component, but most pages don't use it.

**App shell and navigation**
- The sidebar's grey background stops after one screen height. On longer pages the sidebar area turns white
  below that (visible in every desktop capture).
- There's no top bar. The bell and theme toggle float at the top right of each page and appear only on some
  pages: Admin has no bell, while Finance and HR do. The page title sits beside them, so the header layout
  changes from page to page.
- The profile is a small card pinned to the bottom of the sidebar, with no profile menu.
- There's no icon-rail state between desktop and phone: at 1024 px and below, the full sidebar still takes 268 px.
- On a phone, the bottom tab bar covers content in mid-page, as in the HR review capture.
- Only nominations and their detail pages have a breadcrumb or "Back" link. Other detail pages, like an employee
  opened from the list, have none.

**Dark theme**
- Dark mode is opt-in only. The app always starts in light and ignores `prefers-color-scheme`, so the phone
  captures (requested in dark) actually rendered light. **This means dark mode has never been audited by axe.**

**Motion**
- The style sheet has a prefers-reduced-motion block, but the 5-second "run predictions" animation, the row
  reveals and the panel entry animations need checking against it.

## 2. Page by page

**Employee: My growth** (`/my-readiness`)
- The score is a thin grey bar with a tiny "Threshold 23%" label. "Under 1%" has no visual weight, and
  "Not yet recommended" is a small grey pill in the corner.
- The plain-language summary is a dense paragraph inside the score card, not a highlighted card of its own.
- The intro card ("Worked out from your current work record by the EBM (monotonic) model…") puts model jargon at
  the top of an employee's page.
- "What raised and lowered your score" is one-sided for this employee: all eight rows lower the score, and the
  "raises" half is empty, even though the summary says attendance and cross-department projects raised it. The
  list shows the top eight by size, so the raising factors are cut. The two-sided list should show the top
  raisers and the top lowerers separately. This changes only which rows are displayed, not the data.
- Each factor row repeats a small "▼ lowers" tag, which is noisy, and the bar sits far from its label.
- "Your path to promotion" is a numbered list, not a checklist.
- What-if has 17 sliders in a three-column grid, with duplicated "51.5" and "Now: 51.5" text on each. It's long
  and hard to scan.
- On a phone the page is about 5,000 px tall. The bottom tab bar covers part of the score summary.

**Respond to this explanation**
- The two routes are small segmented tabs ("Rate this explanation" / "Correct my record"). Nothing explains
  their difference before you choose, and there are no icons.
- The 1 to 5 agreement scales are small circles with tiny "Disagree"/"Agree" labels. On a phone, "Agree" wraps
  to its own line.
- "Does any factor seem wrong or unfair? (optional)" is a bare disclosure link.

**HR: Review a nomination** (`/nominations/:id`)
- **This is the only page wider than a phone (541 px).** The criteria table (Area / Rating / Example) doesn't
  reflow, and the Example column runs off the screen.
- The manager's case and the model's view are stacked, not side by side, so comparing them means scrolling.
- The pending-correction note and the hold are at the bottom. The status pill "Waiting for HR" sits next to the
  bell, where it reads like part of the toolbar.
- "Your decision is on hold…" appears twice: inside the committee note and again in a callout below it.
- Each factor row shows a raw contribution (−1.19) with no label to explain it.

**HR: Record corrections** (`/corrections`)
- Fairly clear already. The Confirm and Reject boxes are grey-on-grey, the "In the record 5 / Asked for 8" values
  sit far to the right of their labels, and there's no visual "5 → 8" change.
- The disabled "Reject the request" button is nearly invisible.

**HR: Feedback dashboard** (`/feedback`)
- No charts at all: everything is number tiles and sentences.
- Withheld values show as a lone dash "–" plus a long sentence. Small counts should read "<3", as the page's own
  note promises.
- Filters sit in a large card with unaligned labels. The "From" and "To" fields are narrower than the selects.
- The tiles are tall with lots of empty space, and the label/value/note order varies.

**HR: All employees** and **Manager: My team** (`/employees`, `/team`)
- The table has no sticky header, no zebra or hover rows, and no sort indicators. Readiness isn't
  right-aligned, and the "Model's view" column is far from "Readiness".
- The "Run the readiness predictions" banner is a full card with a large button, which is fine, but it competes
  with the table.
- Names are underlined links, which is noisy in a long list.

**HR: Decision log, Model registry, Live fairness**
- These follow the same table style as above: no sticky header and inconsistent number alignment. The model
  registry and fairness pages mix stat tiles, tables and long explanatory text with weak hierarchy.

**HR: Predict & explain** (`/employees/:id`)
- This uses the same layout as My growth, so the same problems apply. There's no breadcrumb back to the employee
  list.

**HR: Employee form and import**
- These are long single-column forms with no grouping into sections, and every field gets the same weight.

**Manager: Nominations, and the recommendation form** (`NominateBox`)
- The four 1 to 5 criteria and their example boxes aren't visually grouped. The title, start date and pay rise
  fields read as part of the same block.

**Finance: Pay sign-off** (`/finance`)
- This is close to the target already. The "Review" button is a large pill, the "With Finance" status pill
  relies on blue alone, and the empty "Signed off this year, by department" card takes a full panel.

**Auditor: Overview, Decisions, Audit trail, Feedback**
- These are read-only, but nothing on the page says so. The audit trail table is dense and has no sticky header.

**Admin: Overview** (`/`)
- System health is a cluster of coloured pills with text in between ("OK: web API", "Below 0.8, within chance at
  this size"), which is hard to scan. A row per component with a status icon and word would be clearer.
- The Drift table header "Chance alone reaches" is unclear. "Level" uses colour plus a word, which is good, but
  the pills are small.
- Recent activity dates use the stretched-hyphen problem described above.
- There's no bell on this page, although other roles' pages have one.

**Admin: Users, Activity log, Email, Demo requests**
- These have the same table issues. Users has many row actions as text buttons, and Email mixes settings and the
  outbox in one long page.

**Account** (`/account`)
- This is a long page of stacked cards (profile, password, sessions) with no section navigation.

**Landing page** (`/`)
- The hero is left-aligned text with two small buttons and no visual on the right, so it feels empty at
  1366 px.
- Screenshots in the page are old captures. One still shows the earlier layout, and the second is cropped
  mid-slider.
- "How it works" uses arrow characters "→" between the cards, which don't reflow on a phone.
- The "How it did in testing" numbers are 0.88 / 89% / 0.47 / 20, with no visual grouping or units on the
  tiles.
- The footer is minimal: the full thesis title, but no columns or links grouped by purpose.

**Login** (`/login`)
- Clean and centred, but it uses the generic "ML" gradient tile, not a MeritLens wordmark. The blurred colour
  blobs in the background are decorative and slightly muddy.
- The 1366 px desktop capture renders the username field already focused, which is fine.

## 3. Accessibility notes (beyond axe's 0 findings)

- Dark mode hasn't been audited (see Dark theme above).
- Disabled-button text contrast is very low (see Colour and identity above).
- Small text at 11 to 12.5 px makes reading harder, especially for the 1 to 5 scale labels.
- Status pills like "With Finance", "Waiting for HR" and "OK: web API" include words, so they're fine. The
  coloured bullet dots in "Needs your attention" rely on colour, but each one has a text title next to it.
- Focus rings exist, a 4 px blue glow, but they're faint on the grey sidebar.
- Icon-only buttons (the bell, the theme toggle, the sidebar collapse, the sign-out icon) need checking for an
  `aria-label` on each.

## 4. Things to keep

These rules are good and stay as they are:
- Teal for "raises" and orange for "lowers" are kept only for data.
- "Not yet recommended" is neutral grey, never red.
- Status is always shown with a word.
- "<3" protects small groups.

Browser checks depend on some selectors, so they'll be preserved or updated together with the checks:
`.agree-option`, `button[aria-pressed]`, `.respond-body`, `.field-hint`, `.bell button`, `.pager`, `.intro-actions`,
`.nav-group-head`, `.alert-error`, `.just-scored` and `.score-pending`.

## 5. Questions before redesigning

1. **Navy and teal versus the current blue.** The brief says to keep the navy and teal identity, but the app is
   currently Apple blue. Navy (`#0f2a44`) with teal actions (`#0b7a6e`) was the identity before commit bcdd055.
   Restoring it has one conflict: teal is also the "raises your score" data colour, and the current design
   deliberately never uses a data colour for buttons. I suggest **navy for primary actions and the sidebar
   accent, teal kept only for "raises" data and small highlights**. That keeps the rule intact and keeps the
   identity.
2. **Dark mode default.** Should the app follow the computer's `prefers-color-scheme` on first visit, with the
   toggle still overriding it? Today it always starts in light.
3. **Score as a percentage.** The score shows as "under 1%" and "23%". The brief says never to call it a
   probability or a chance, and the text doesn't, but a "%" still reads that way to many people. Should the gauge
   show it as a 0 to 100 readiness score ("Readiness 1 / 100, threshold 23")? This is display only: the API
   value doesn't change.

## 6. Decisions taken

1. **Navy and teal.** Navy (`#1E3A5F`, with a `#0F2A44` sidebar) is used for primary actions and the sidebar.
   Teal is used only for the "raises" data colour and small highlights (the active-menu marker and focus rings).
2. **Dark mode** now follows the computer's setting on a first visit. The toggle still overrides it and is
   remembered in the browser.
3. **Score format: kept as a percentage, which differs from the suggestion.** The plain-language summary
   ("Readiness is under 1%, below the 23% threshold…"), the what-if result and the tips all come from the API as
   text with percentages. Showing "1 / 100" in the gauge beside those sentences would put two formats for the same
   number on one screen, and changing the sentences would mean changing the backend. So the score stays a
   percentage, always labelled "Readiness score" and read against its threshold, and nothing on screen calls it a
   probability or a chance. The helper text still says it "describes past decisions, so it isn't a promise".

## 7. What changed

After screenshots: `docs/screenshots/after-ui/`. Every page has 4 shots: desktop (1366px) and phone (390px), each
in light and dark. axe-core results are in `axe.json`. Thesis figures (PNG, 1600px, light) are in
`docs/screenshots/thesis/`.

**Results:** 0 axe-core findings on all 39 pages (desktop light, desktop dark, phone dark), and no page is wider
than a 390px phone screen. All 7 browser checks and all 322 backend tests pass, and `npm run build` finishes with
no errors or warnings. Backend logic, the model, API responses and permissions are unchanged.

### Everywhere

- **Design system:** tokens in `frontend/src/tokens.css` (light and dark), components styled once in `styles.css`.
  This is described in HOW_IT_WORKS.md, under "Design system".
- **Type:**
  - Montserrat, installed locally; the Google Fonts link in `index.html` is gone.
  - One 32/24/20/16/14/12 type scale replaces the 23 sizes there were before.
  - Body text is at least 14px.
  - Tabular figures for scores, tables and KPI tiles.
  - The stretched hyphens in dates ("2026 - 10 - 15") are fixed.
- **Colour:**
  - Navy for actions, teal and orange only for the model's data, and status colours each with a tinted background.
  - Every pair was checked for AA contrast in both themes.
  - Disabled buttons are now readable: a quiet fill with muted text, not faded out.
- **Shape and spacing:** a 4px spacing grid, 8px corners on cards and inputs, 6px on buttons, one soft shadow. The
  gradient icon tiles beside page titles are removed.
- **Shared components replace one-off styles:**
  - New: `Callout`, `Badge` (every status has an icon and a word), `PageLoading`, `SortHeader`, `Pager`, `Modal`,
    `Drawer`, `useConfirm`, toasts.
  - Restyled: `PageHeader`, `Card`, `StatCard`, `Button` (primary, secondary, ghost, danger), `Segmented` tabs,
    `EmptyState`, `LoadError`.
  - Inline styles went from 73 to a handful, each one a computed width or position.
- **App shell:**
  - A full-height navy sidebar with the menu grouped per role.
  - A top bar with the breadcrumb, light/dark switch, the bell (now on every page) and a profile menu.
  - Content up to 1280px wide.
  - An icon rail from 640 to 1023px, and a drawer under 640px. The phone tab bar that covered content is gone.
  - A page opened for the first time now loads inside the frame with a skeleton, instead of a blank "Loading…"
    screen.
- **Tables:** sticky headers, hover rows, right-aligned numbers, sort arrows (with `aria-sort`) on the employee
  list, and pagination on the employee list, decision log and audit trail. Every scrolling table is a labelled,
  keyboard-scrollable region.
- **Loading and errors:** skeletons instead of spinners. Errors say "This couldn't be loaded", give the reason, and
  offer "Try again".
- **Keyboard:**
  - A "Skip to the page" link and a visible teal focus ring.
  - Escape closes the profile menu, notifications, modals, drawers and the phone menu, and focus returns to the
    opener.
  - Focus moves into the phone drawer when it opens.
  - Every icon-only button has an `aria-label`.
  - The browser's own confirm boxes (Users page) are now an accessible modal.
- **Motion:** 150–200 ms fades and slides only, and none when the computer asks for reduced motion.

### Employee: My growth

- **The score:** a half-circle gauge with the threshold marked and labelled, "Readiness score" under the number,
  and a "Recommended" or "Not yet recommended" badge with an icon.
- **The plain-language summary** is in its own highlighted "In plain words" card beside the gauge.
- **"What raised and lowered your score"** is now two-sided: "Raised the score" (teal) and "Lowered the score"
  (orange), up to five each, all bars on one scale. Before, only factors that lowered the score were shown for this
  employee.
- **"Your path to promotion"** is a checklist.
- **What-if:** sliders are tidier tiles. "Now: …" appears only when a slider has moved, and a moved slider is
  highlighted.
- **"Show technical details"** stays collapsed. The run line at the top is shorter, and the model jargon has moved
  into "How it was worked out".

### Respond to this explanation

- **The two routes** are two cards with icons and a short description each: "Rate this explanation" and "Correct my
  record". The whole card can be clicked, and the chosen card is outlined in navy.
- **The 1–5 scales** are larger square buttons with "Disagree" and "Agree" at the ends.

### HR

- **Predict and explain** (`/employees/:id`):
  - The same gauge, summary, factors and tips as My growth.
  - A clearer "Predict and explain" run card.
  - The breadcrumb leads back to the list.
- **Nomination review:**
  - The committee note (a record correction is pending, and the hold) is a highlighted warning card at the top.
  - The manager's recommendation and the model's view are side by side from 1100px wide.
  - The criteria are a list that reflows; this was the page that was 541px wide on a phone.
  - The duplicate "on hold" message is removed.
  - The status badge sits beside the title, not by the bell.
- **Correction queue:**
  - The change is shown as "In the record 5 → Asked for 8".
  - The evidence is quoted.
  - Confirm and Reject are two cards with icons.
  - Helpful empty state.
- **Decision log:** pagination, right-aligned model scores, status badges.
- **Feedback dashboard:**
  - Export CSV is the page's primary action, and the filters sit in one row.
  - KPI tiles.
  - Charts in one style: meters for "Clear" and "Useful", a stacked bar for correction outcomes, a bar list for
    contested factors, and a stacked bar for decisions against the model.
  - Values are written beside every mark; withheld values show "–" with the reason, and small counts show "<3".
- **Pay-rise policy:** an inline form, and a toast confirms the save.
- **All employees:** sortable Name, Department and Readiness columns, right-aligned scores, and the shared pager.

### Manager

- **Team readiness table:** as for HR.
- **Recommendation form:**
  - The four criteria each have a 1–5 button scale with the rating in words, and an example box, in two columns.
  - The model's view is a callout.
  - The title, start date and pay rise fields are grouped.

### Finance

- **Sign-off queue:** a clean table with status badges. "Review" opens a drawer with what is being signed off, its
  history, and Sign off or Send back. A toast confirms the action.
- **Empty states** explain what will appear.

### Auditor

- **Overview:** says the pages are read-only.
- **Read-only pages:** the decision log, audit trail (with a paged, labelled table and callouts for the chain
  check), live fairness and model registry use the shared components.

### Admin

- **Overview:** system health is a list, one row per part with an icon and a word (OK, Problem, Check, Note) and
  its detail underneath, instead of a cluster of pills. The drift table has right-aligned numbers and a clearer
  column name ("PSI from chance alone"). Recent activity has column headings.
- **Users:**
  - The account-type tabs sit under the title.
  - Row actions are compact ghost buttons.
  - Status and role are badges.
  - Confirmations use the modal.
  - The team editor opens in a drawer.
- **Activity log, Email and Demo requests:** use callouts, badges and the shared table style.

### Landing page and login

- **Landing page:**
  - The hero has the title, a one-line value statement and the app beside it in a window frame.
  - "How it works": three numbered steps joined by a line (Predict, Explain, Respond).
  - Six feature cards.
  - Two screenshots of the new interface.
  - A "Fairness and privacy" section.
  - Result tiles.
  - A navy closing band.
  - A footer with product and get-started columns.
  - The screenshots were recaptured from the new interface (`frontend/public/landing/`).
- **Login:** a clean centred card under the MeritLens wordmark, without the blurred background blobs.
