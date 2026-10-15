// The six roles, how they're named on screen, and the menu each one sees.
// The backend checks roles on every request; this file only decides what to show.
import { Banknote, BarChart3, BookCheck, Boxes, ClipboardPen, MessageSquareText, Brain, CalendarCheck, ClipboardCheck, Gauge, Landmark, LayoutGrid, Mail, Scale, ScrollText, ShieldCheck, TrendingUp, UserCog, UserRound, Users } from "lucide-react";

export const ROLE_NAMES = {
  employee: "Employee",
  manager: "Manager",
  hr: "HR",
  admin: "Admin",
  finance: "Finance",
  auditor: "Compliance auditor",
};

export const ROLE_DESCRIPTIONS = {
  employee: "See your readiness score, why, and tips to improve; rate the explanation, or ask HR to correct your record.",
  manager: "See your team's scores, and nominate team members for promotion.",
  hr: "See all employees, decide on nominations, confirm record corrections, and release new model versions.",
  admin: "Create and manage user accounts, and view the activity log, system health and audit trail.",
  finance: "Sign off the pay rise of each approved promotion, or send it back to HR with a reason.",
  auditor: "Check decisions, the audit trail, the model and its fairness, read-only. Never sees an individual's feedback.",
};

const OVERVIEW = { to: "/", label: "Overview", icon: LayoutGrid };
const MODEL = { to: "/model", label: "How the model works", icon: Brain };
const REGISTRY = { to: "/models", label: "Model registry", icon: Boxes };
const FAIRNESS = { to: "/fairness", label: "Live fairness", icon: Scale };
const AUDIT = { to: "/audit", label: "Audit trail", icon: ShieldCheck };
export const ACCOUNT = { group: "Account", icon: UserRound, items: [{ to: "/account", label: "My profile", icon: UserRound }] };

// Menu per role: single links and groups that open and close, so the sidebar stays short
export const MENU = {
  employee: [OVERVIEW,
    { group: "Promotion", icon: TrendingUp, items: [{ to: "/my-readiness", label: "My growth", icon: Gauge }, MODEL] }],
  manager: [OVERVIEW,
    { group: "Promotion", icon: TrendingUp, items: [
      { to: "/team", label: "My team", icon: Users },
      { to: "/nominations", label: "My nominations", icon: ClipboardCheck }, MODEL] }],
  hr: [OVERVIEW,
    { group: "Promotion", icon: TrendingUp, items: [
      { to: "/employees", label: "All employees", icon: Users },
      { to: "/nominations", label: "Nominations", icon: ClipboardCheck },
      { to: "/decisions", label: "Decision log", icon: BookCheck }, MODEL] },
    { group: "Feedback", icon: MessageSquareText, items: [
      { to: "/corrections", label: "Record corrections", icon: ClipboardPen },
      { to: "/feedback", label: "Feedback dashboard", icon: BarChart3 }] },
    { group: "Governance", icon: Landmark, items: [REGISTRY, FAIRNESS] }],
  admin: [OVERVIEW,
    { group: "Administration", icon: UserCog, items: [
      { to: "/admin/users", label: "Users", icon: UserCog },
      { to: "/admin/activity", label: "Activity log", icon: ScrollText },
      { to: "/admin/email", label: "Email", icon: Mail },
      { to: "/admin/demo-requests", label: "Demo requests", icon: CalendarCheck }] },
    { group: "Governance", icon: Landmark, items: [REGISTRY, FAIRNESS, AUDIT] }],
  finance: [OVERVIEW,
    { group: "Finance", icon: Banknote, items: [{ to: "/finance", label: "Pay sign-off", icon: Banknote }] }],
  auditor: [OVERVIEW,
    { group: "Oversight", icon: ShieldCheck, items: [
      { to: "/decisions", label: "Decision log", icon: BookCheck }, AUDIT, FAIRNESS,
      { to: "/feedback", label: "Feedback dashboard", icon: BarChart3 }, REGISTRY, MODEL] }],
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
  employee: ["/", "/my-readiness", "/model"],
  manager: ["/", "/team", "/nominations"],
  hr: ["/", "/nominations", "/corrections"],
  admin: ["/", "/admin/users", "/admin/activity"],
  finance: ["/", "/finance"],
  auditor: ["/", "/decisions", "/audit"],
};
// Short names that fit under a tab icon
export const SHORT_LABELS = {
  "/": "Home", "/my-readiness": "Growth", "/team": "Team",
  "/nominations": "Nominations", "/corrections": "Corrections", "/admin/users": "Users", "/admin/activity": "Activity", "/finance": "Pay",
  "/decisions": "Decisions", "/model": "Model", "/feedback": "Feedback",
  "/models": "Models", "/fairness": "Fairness", "/audit": "Audit",
};
