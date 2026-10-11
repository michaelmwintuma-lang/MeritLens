# Phase 7: before and after

Screenshots of the main pages for each role, on a computer (1366 wide, light theme) and a phone (390 wide, dark
theme), taken from a throwaway copy of the app with the made-up demo data:

```
python scripts/browser_test.py scripts/ui_capture.js docs/screenshots/<folder>
```

The same script runs the axe-core accessibility audit (WCAG 2.1 A and AA). Its findings are in `axe.json` in each
folder.

- **Before** (light theme on a computer only): no findings. The dark theme on a phone wasn't audited then.
- **After, first run** (both themes): 4 findings, all `scrollable-region-focusable`. On a phone, wide tables
  scroll sideways, and keyboard users couldn't reach them. Table areas can now take keyboard focus.
- **After, final run** (both themes): no findings on any page.

An automated audit can't judge everything. These were also checked by looking at the pages: the order of the
explanation page, plain language, loading and error states, and that every status is written in words, not shown
by colour alone.

The set first had 17 pages. Two of them (the employee's report form and HR's report inbox) belonged to anonymous
reporting, which was removed afterwards; their screenshots and audit entries were taken out, leaving 15.

| Page | Before | After | Findings after |
|---|---|---|---|
| landing | [computer](phase7-before/landing-desktop.webp) · [phone](phase7-before/landing-phone.webp) | [computer](phase7-after/landing-desktop.webp) · [phone](phase7-after/landing-phone.webp) | 0 |
| login | [computer](phase7-before/login-desktop.webp) · [phone](phase7-before/login-phone.webp) | [computer](phase7-after/login-desktop.webp) · [phone](phase7-after/login-phone.webp) | 0 |
| employee-home | [computer](phase7-before/employee-home-desktop.webp) · [phone](phase7-before/employee-home-phone.webp) | [computer](phase7-after/employee-home-desktop.webp) · [phone](phase7-after/employee-home-phone.webp) | 0 |
| employee-growth | [computer](phase7-before/employee-growth-desktop.webp) · [phone](phase7-before/employee-growth-phone.webp) | [computer](phase7-after/employee-growth-desktop.webp) · [phone](phase7-after/employee-growth-phone.webp) | 0 |
| manager-team | [computer](phase7-before/manager-team-desktop.webp) · [phone](phase7-before/manager-team-phone.webp) | [computer](phase7-after/manager-team-desktop.webp) · [phone](phase7-after/manager-team-phone.webp) | 0 |
| hr-home | [computer](phase7-before/hr-home-desktop.webp) · [phone](phase7-before/hr-home-phone.webp) | [computer](phase7-after/hr-home-desktop.webp) · [phone](phase7-after/hr-home-phone.webp) | 0 |
| hr-employees | [computer](phase7-before/hr-employees-desktop.webp) · [phone](phase7-before/hr-employees-phone.webp) | [computer](phase7-after/hr-employees-desktop.webp) · [phone](phase7-after/hr-employees-phone.webp) | 0 |
| hr-corrections | [computer](phase7-before/hr-corrections-desktop.webp) · [phone](phase7-before/hr-corrections-phone.webp) | [computer](phase7-after/hr-corrections-desktop.webp) · [phone](phase7-after/hr-corrections-phone.webp) | 0 |
| hr-feedback-dashboard | [computer](phase7-before/hr-feedback-dashboard-desktop.webp) · [phone](phase7-before/hr-feedback-dashboard-phone.webp) | [computer](phase7-after/hr-feedback-dashboard-desktop.webp) · [phone](phase7-after/hr-feedback-dashboard-phone.webp) | 0 |
| hr-decisions | [computer](phase7-before/hr-decisions-desktop.webp) · [phone](phase7-before/hr-decisions-phone.webp) | [computer](phase7-after/hr-decisions-desktop.webp) · [phone](phase7-after/hr-decisions-phone.webp) | 0 |
| auditor-home | [computer](phase7-before/auditor-home-desktop.webp) · [phone](phase7-before/auditor-home-phone.webp) | [computer](phase7-after/auditor-home-desktop.webp) · [phone](phase7-after/auditor-home-phone.webp) | 0 |
| model | [computer](phase7-before/model-desktop.webp) · [phone](phase7-before/model-phone.webp) | [computer](phase7-after/model-desktop.webp) · [phone](phase7-after/model-phone.webp) | 0 |
| finance-home | [computer](phase7-before/finance-home-desktop.webp) · [phone](phase7-before/finance-home-phone.webp) | [computer](phase7-after/finance-home-desktop.webp) · [phone](phase7-after/finance-home-phone.webp) | 0 |
| admin-home | [computer](phase7-before/admin-home-desktop.webp) · [phone](phase7-before/admin-home-phone.webp) | [computer](phase7-after/admin-home-desktop.webp) · [phone](phase7-after/admin-home-phone.webp) | 0 |
| admin-users | [computer](phase7-before/admin-users-desktop.webp) · [phone](phase7-before/admin-users-phone.webp) | [computer](phase7-after/admin-users-desktop.webp) · [phone](phase7-after/admin-users-phone.webp) | 0 |
