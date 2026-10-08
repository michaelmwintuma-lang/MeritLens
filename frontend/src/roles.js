// The four roles, how they're named on screen, and the menu each one sees.
// The backend checks roles on every request; this file only decides what to show.
import { Banknote, BookCheck, Brain, CalendarCheck, ClipboardCheck, FileSearch, Gauge, Inbox, LayoutGrid, Mail, Megaphone, ScrollText, ShieldCheck, TrendingUp, UserCog, UserRound, Users } from "lucide-react";

export const ROLE_NAMES = {
  employee: "Employee",
  manager: "Manager",
  hr: "HR",
  admin: "Admin",
  finance: "Finance",
};

export const ROLE_DESCRIPTIONS = {
  employee: "See your own readiness score, its explanation and tips to improve; report a concern anonymously.",
  manager: "See your team's scores, nominate team members for promotion, and report a concern anonymously.",
  hr: "See all employees, decide on nominations, and handle anonymous reports.",
  admin: "Create and manage user accounts, and view the activity log.",
  finance: "Sign off the pay rise of each approved promotion, or send it back to HR with a reason.",
};

// Who uses the anonymous reporting pages (HR handles reports in the report inbox instead)
export const REPORTER_ROLES = ["employee", "manager"];

const OVERVIEW = { to: "/", label: "Overview", icon: LayoutGrid };
const MODEL = { to: "/model", label: "How the model works", icon: Brain };
const REPORTING = {
  group: "Reporting", icon: ShieldCheck, items: [
    { to: "/report", label: "Report anonymously", icon: Megaphone },
    { to: "/my-report", label: "Check my report", icon: FileSearch },
  ],
};
export const ACCOUNT = { group: "Account", icon: UserRound, items: [{ to: "/account", label: "My profile", icon: UserRound }] };

// Menu per role: single links and groups that open and close, so the sidebar stays short
export const MENU = {
  employee: [OVERVIEW,
    { group: "Promotion", icon: TrendingUp, items: [{ to: "/my-readiness", label: "My readiness", icon: Gauge }, MODEL] },
    REPORTING],
  manager: [OVERVIEW,
    { group: "Promotion", icon: TrendingUp, items: [
      { to: "/team", label: "My team", icon: Users },
      { to: "/nominations", label: "My nominations", icon: ClipboardCheck }, MODEL] },
    REPORTING],
  hr: [OVERVIEW,
    { group: "Promotion", icon: TrendingUp, items: [
      { to: "/employees", label: "All employees", icon: Users },
      { to: "/nominations", label: "Nominations", icon: ClipboardCheck },
      { to: "/decisions", label: "Decision log", icon: BookCheck }, MODEL] },
    { group: "Reporting", icon: ShieldCheck, items: [{ to: "/reports", label: "Report inbox", icon: Inbox }] }],
  admin: [OVERVIEW,
    { group: "Administration", icon: UserCog, items: [
      { to: "/admin/users", label: "Users", icon: UserCog },
      { to: "/admin/activity", label: "Activity log", icon: ScrollText },
      { to: "/admin/email", label: "Email", icon: Mail },
      { to: "/admin/demo-requests", label: "Demo requests", icon: CalendarCheck }] }],
  finance: [OVERVIEW,
    { group: "Finance", icon: Banknote, items: [{ to: "/finance", label: "Pay sign-off", icon: Banknote }] }],
};

// Admins an admin has allowed to view employee data (read-only) get the employee pages too
const EMPLOYEE_DATA = { group: "Employee data", icon: TrendingUp, items: [
  { to: "/employees", label: "All employees", icon: Users }, MODEL] };

/** The menu for this signed-in user. */
export function menuFor(user) {
  if (user.role === "admin" && user.can_view_employees) return [...MENU.admin, EMPLOYEE_DATA];
  return MENU[user.role];
}

// On a phone the menu becomes a tab bar at the bottom: three pages per role, plus "Menu" for everything else
export const PHONE_TABS = {
  employee: ["/", "/my-readiness", "/report"],
  manager: ["/", "/team", "/report"],
  hr: ["/", "/nominations", "/reports"],
  admin: ["/", "/admin/users", "/admin/activity"],
  finance: ["/", "/finance"],
};
// Short names that fit under a tab icon
export const SHORT_LABELS = {
  "/": "Home", "/my-readiness": "Readiness", "/report": "Report", "/team": "Team",
  "/nominations": "Nominations", "/reports": "Inbox", "/admin/users": "Users", "/admin/activity": "Activity", "/finance": "Pay",
};
