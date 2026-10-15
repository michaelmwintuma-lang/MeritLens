// The six roles, how they're named on screen, and the menu each one sees.
// The backend checks roles on every request; this file only decides what to show.
import { Banknote, BarChart3, BookCheck, Boxes, Brain, CalendarCheck, ClipboardCheck, ClipboardPen, Gauge, LayoutGrid, Mail, Scale, ScrollText, ShieldCheck, UserCog, Users } from "lucide-react";

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

// Menu per role: the overview, then the pages in named groups
export const MENU = {
  employee: [OVERVIEW,
    { group: "Promotion", items: [{ to: "/my-readiness", label: "My growth", icon: Gauge }, MODEL] }],
  manager: [OVERVIEW,
    { group: "Promotion", items: [
      { to: "/team", label: "My team", icon: Users },
      { to: "/nominations", label: "My nominations", icon: ClipboardCheck }, MODEL] }],
  hr: [OVERVIEW,
    { group: "Promotion", items: [
      { to: "/employees", label: "All employees", icon: Users },
      { to: "/nominations", label: "Nominations", icon: ClipboardCheck },
      { to: "/decisions", label: "Decision log", icon: BookCheck }, MODEL] },
    { group: "Feedback", items: [
      { to: "/corrections", label: "Record corrections", icon: ClipboardPen },
      { to: "/feedback", label: "Feedback dashboard", icon: BarChart3 }] },
    { group: "Governance", items: [REGISTRY, FAIRNESS] }],
  admin: [OVERVIEW,
    { group: "Administration", items: [
      { to: "/admin/users", label: "Users", icon: UserCog },
      { to: "/admin/activity", label: "Activity log", icon: ScrollText },
      { to: "/admin/email", label: "Email", icon: Mail },
      { to: "/admin/demo-requests", label: "Demo requests", icon: CalendarCheck }] },
    { group: "Governance", items: [REGISTRY, FAIRNESS, AUDIT] }],
  finance: [OVERVIEW,
    { group: "Finance", items: [{ to: "/finance", label: "Pay sign-off", icon: Banknote }] }],
  auditor: [OVERVIEW,
    { group: "Oversight", items: [
      { to: "/decisions", label: "Decision log", icon: BookCheck }, AUDIT, FAIRNESS,
      { to: "/feedback", label: "Feedback dashboard", icon: BarChart3 }, REGISTRY, MODEL] }],
};

// Admins an admin has allowed to view employee data (read-only) get the employee pages too
const EMPLOYEE_DATA = { group: "Employee data", items: [
  { to: "/employees", label: "All employees", icon: Users }, MODEL] };

/** The menu for this signed-in user. */
export function menuFor(user) {
  if (user.role === "admin" && user.can_view_employees) return [...MENU.admin, EMPLOYEE_DATA];
  return MENU[user.role];
}
