// Pages and who may open them.
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import { REPORTER_ROLES } from "./roles";
import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";
import PublicLayout from "./pages/public/PublicLayout";
import PublicHome from "./pages/public/Home";
import Approach from "./pages/public/Approach";
import PromotionPage from "./pages/public/PromotionPage";
import ReportingPage from "./pages/public/ReportingPage";
import Privacy from "./pages/public/Privacy";
import BookDemo from "./pages/public/BookDemo";
import Login from "./pages/Login";
import Home from "./pages/Home";
import Account from "./pages/Account";
import Users from "./pages/admin/Users";
import ActivityLog from "./pages/admin/ActivityLog";
import Email from "./pages/admin/Email";
import DemoRequests from "./pages/admin/DemoRequests";
import Readiness from "./pages/promotion/Readiness";
import EmployeeList from "./pages/promotion/EmployeeList";
import EmployeeForm from "./pages/promotion/EmployeeForm";
import ImportEmployees from "./pages/promotion/ImportEmployees";
import ModelOverview from "./pages/promotion/ModelOverview";
import Nominations from "./pages/promotion/Nominations";
import PaySignOff from "./pages/finance/PaySignOff";
import ReviewNomination from "./pages/promotion/ReviewNomination";
import DecisionLog from "./pages/promotion/DecisionLog";
import Report from "./pages/reporting/Report";
import CheckReport from "./pages/reporting/CheckReport";
import ReportInbox from "./pages/reporting/ReportInbox";
import ReportCase from "./pages/reporting/ReportCase";

/** Shows the page only to the listed roles. The backend enforces the same rule on every request. */
function OnlyFor({ roles, children }) {
  const { user } = useAuth();
  if (roles.includes(user.role)) return children;
  return <div className="card"><h1>Not available</h1><p className="muted">Your role doesn't have access to this page.</p></div>;
}

export default function App() {
  const { user, loading } = useAuth();
  const { pathname } = useLocation();
  if (loading) return <p className="center-page muted">Loading…</p>;

  // Not signed in: the public website (one page per menu item) and the sign-in page
  if (!user) {
    return (
      <ErrorBoundary resetKey={pathname}>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<PublicHome />} />
          <Route path="approach" element={<Approach />} />
          <Route path="promotion" element={<PromotionPage />} />
          <Route path="reporting" element={<ReportingPage />} />
          <Route path="privacy" element={<Privacy />} />
          <Route path="demo" element={<BookDemo />} />
        </Route>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
      </ErrorBoundary>
    );
  }
  // Accounts with a temporary password must choose their own before using anything else
  if (user.must_change_password && pathname !== "/account") return <Navigate to="/account" replace />;

  // HR sees every employee; so do admins who were given "can view employee data" (read-only)
  const viewAll = user.role === "admin" && user.can_view_employees ? ["hr", "admin"] : ["hr"];

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="account" element={<Account />} />
        <Route path="admin/users" element={<OnlyFor roles={["admin"]}><Users /></OnlyFor>} />
        <Route path="admin/activity" element={<OnlyFor roles={["admin"]}><ActivityLog /></OnlyFor>} />
        <Route path="admin/email" element={<OnlyFor roles={["admin"]}><Email /></OnlyFor>} />
        <Route path="admin/demo-requests" element={<OnlyFor roles={["admin"]}><DemoRequests /></OnlyFor>} />
        <Route path="my-readiness" element={<OnlyFor roles={["employee"]}><Readiness /></OnlyFor>} />
        <Route path="team" element={<OnlyFor roles={["manager"]}><EmployeeList /></OnlyFor>} />
        <Route path="employees" element={<OnlyFor roles={viewAll}><EmployeeList /></OnlyFor>} />
        <Route path="employees/new" element={<OnlyFor roles={["hr"]}><EmployeeForm /></OnlyFor>} />
        <Route path="employees/import" element={<OnlyFor roles={["hr"]}><ImportEmployees /></OnlyFor>} />
        <Route path="employees/:id/edit" element={<OnlyFor roles={["hr"]}><EmployeeForm /></OnlyFor>} />
        <Route path="employees/:id" element={<OnlyFor roles={[...viewAll, "manager"]}><Readiness /></OnlyFor>} />
        <Route path="model" element={<OnlyFor roles={["employee", "manager", "auditor", ...viewAll]}><ModelOverview /></OnlyFor>} />
        <Route path="nominations" element={<OnlyFor roles={["manager", "hr"]}><Nominations /></OnlyFor>} />
        <Route path="nominations/:id" element={<OnlyFor roles={["hr"]}><ReviewNomination /></OnlyFor>} />
        <Route path="decisions" element={<OnlyFor roles={["hr", "auditor"]}><DecisionLog /></OnlyFor>} />
        <Route path="finance" element={<OnlyFor roles={["finance"]}><PaySignOff /></OnlyFor>} />
        {/* Anonymous reporting: employees and managers. HR handles reports in the inbox. */}
        <Route path="report" element={<OnlyFor roles={REPORTER_ROLES}><Report /></OnlyFor>} />
        <Route path="my-report" element={<OnlyFor roles={REPORTER_ROLES}><CheckReport /></OnlyFor>} />
        <Route path="reports" element={<OnlyFor roles={["hr"]}><ReportInbox /></OnlyFor>} />
        <Route path="reports/:caseId" element={<OnlyFor roles={["hr"]}><ReportCase /></OnlyFor>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
