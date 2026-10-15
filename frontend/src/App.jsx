// Pages and who may open them.
import { Suspense, lazy } from "react";
import { Loader2, Lock } from "lucide-react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import ErrorBoundary from "./components/ErrorBoundary";
import { EmptyState } from "./components/ui";
import PublicLayout from "./pages/public/PublicLayout";
import PublicHome from "./pages/public/Home";
import Login from "./pages/Login";

// Only the landing page and sign-in load straight away; every other page is fetched the first time it's opened
const Layout = lazy(() => import("./components/Layout"));
const Approach = lazy(() => import("./pages/public/Approach"));
const PromotionPage = lazy(() => import("./pages/public/PromotionPage"));
const Privacy = lazy(() => import("./pages/public/Privacy"));
const BookDemo = lazy(() => import("./pages/public/BookDemo"));
const Home = lazy(() => import("./pages/Home"));
const Account = lazy(() => import("./pages/Account"));
const Users = lazy(() => import("./pages/admin/Users"));
const ActivityLog = lazy(() => import("./pages/admin/ActivityLog"));
const Email = lazy(() => import("./pages/admin/Email"));
const DemoRequests = lazy(() => import("./pages/admin/DemoRequests"));
const Readiness = lazy(() => import("./pages/promotion/Readiness"));
const EmployeeList = lazy(() => import("./pages/promotion/EmployeeList"));
const EmployeeForm = lazy(() => import("./pages/promotion/EmployeeForm"));
const ImportEmployees = lazy(() => import("./pages/promotion/ImportEmployees"));
const ModelOverview = lazy(() => import("./pages/promotion/ModelOverview"));
const Nominations = lazy(() => import("./pages/promotion/Nominations"));
const PaySignOff = lazy(() => import("./pages/finance/PaySignOff"));
const ReviewNomination = lazy(() => import("./pages/promotion/ReviewNomination"));
const DecisionLog = lazy(() => import("./pages/promotion/DecisionLog"));
const ModelRegistry = lazy(() => import("./pages/governance/ModelRegistry"));
const LiveFairness = lazy(() => import("./pages/governance/LiveFairness"));
const AuditTrail = lazy(() => import("./pages/governance/AuditTrail"));
const Corrections = lazy(() => import("./pages/feedback/Corrections"));
const FeedbackDashboard = lazy(() => import("./pages/feedback/FeedbackDashboard"));

/**
 * /login once signed in: go where the person was heading (a link can pass { next: "/some-page" }), or to their
 * overview. Only addresses inside the app are followed.
 */
function AfterSignIn() {
  const next = useLocation().state?.next;
  return <Navigate to={typeof next === "string" && next.startsWith("/") && !next.startsWith("//") ? next : "/"} replace />;
}

/** Shows the page only to the listed roles. The backend enforces the same rule on every request. */
function OnlyFor({ roles, children }) {
  const { user } = useAuth();
  if (roles.includes(user.role)) return children;
  return <div className="card"><EmptyState icon={Lock} title="Not available" text="Your role doesn't have access to this page." /></div>;
}

/** While the app itself loads (before the menu can be drawn). */
function AppLoading() {
  return <div className="center-page"><p className="loading" role="status"><Loader2 size={18} className="spin" aria-hidden="true" />Loading…</p></div>;
}

export default function App() {
  const { user, loading } = useAuth();
  const { pathname } = useLocation();
  if (loading) return <AppLoading />;

  // Not signed in: the public website (one page per menu item) and the sign-in page
  if (!user) {
    return (
      <ErrorBoundary resetKey={pathname}>
      <Suspense fallback={<AppLoading />}>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<PublicHome />} />
          <Route path="approach" element={<Approach />} />
          <Route path="promotion" element={<PromotionPage />} />
          <Route path="privacy" element={<Privacy />} />
          <Route path="demo" element={<BookDemo />} />
        </Route>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
      </Suspense>
      </ErrorBoundary>
    );
  }
  // Accounts with a temporary password must choose their own before using anything else
  if (user.must_change_password && pathname !== "/account") return <Navigate to="/account" replace />;

  // HR sees every employee; so do admins who were given "can view employee data" (read-only)
  const viewAll = user.role === "admin" && user.can_view_employees ? ["hr", "admin"] : ["hr"];

  return (
    <Suspense fallback={<AppLoading />}>
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
        <Route path="models" element={<OnlyFor roles={["hr", "admin", "auditor"]}><ModelRegistry /></OnlyFor>} />
        <Route path="fairness" element={<OnlyFor roles={["hr", "admin", "auditor"]}><LiveFairness /></OnlyFor>} />
        <Route path="audit" element={<OnlyFor roles={["admin", "auditor"]}><AuditTrail /></OnlyFor>} />
        <Route path="corrections" element={<OnlyFor roles={["hr"]}><Corrections /></OnlyFor>} />
        <Route path="feedback" element={<OnlyFor roles={["hr", "auditor"]}><FeedbackDashboard /></OnlyFor>} />
        <Route path="finance" element={<OnlyFor roles={["finance"]}><PaySignOff /></OnlyFor>} />
        <Route path="login" element={<AfterSignIn />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
    </Suspense>
  );
}
