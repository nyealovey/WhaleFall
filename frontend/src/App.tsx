import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense, useMemo } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ApiError } from "./api/client";
import { useLogin, useLogout, useSession } from "./auth/useSession";
import { Toaster } from "./components/ui/sonner";
import { TooltipProvider } from "./components/ui/tooltip";
import { AppShell } from "./layout/AppShell";
import { filterNavigationForRole, flattenNavigationItems, navigationGroups } from "./navigation";
import { LoginPage } from "./pages/LoginPage";

const DashboardPage = lazy(() => import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const RiskCenterPage = lazy(() => import("./pages/RiskCenterPage").then((module) => ({ default: module.RiskCenterPage })));
const InstancesPage = lazy(() => import("./pages/ListPages").then((module) => ({ default: module.InstancesPage })));
const InstanceDetailPage = lazy(() => import("./pages/ListPages").then((module) => ({ default: module.InstanceDetailPage })));
const DatabaseLedgersPage = lazy(() => import("./pages/ListPages").then((module) => ({ default: module.DatabaseLedgersPage })));
const AccountLedgersPage = lazy(() => import("./pages/ListPages").then((module) => ({ default: module.AccountLedgersPage })));
const CapacityInstancesPage = lazy(() => import("./pages/CapacityPages").then((module) => ({ default: module.CapacityInstancesPage })));
const CapacityDatabasesPage = lazy(() => import("./pages/CapacityPages").then((module) => ({ default: module.CapacityDatabasesPage })));
const InstanceStatisticsPage = lazy(() => import("./pages/StatisticsPages").then((module) => ({ default: module.InstanceStatisticsPage })));
const AccountStatisticsPage = lazy(() => import("./pages/StatisticsPages").then((module) => ({ default: module.AccountStatisticsPage })));
const DatabaseStatisticsPage = lazy(() => import("./pages/StatisticsPages").then((module) => ({ default: module.DatabaseStatisticsPage })));
const HistoryLogsPage = lazy(() => import("./pages/AuditPages").then((module) => ({ default: module.HistoryLogsPage })));
const AccountChangeLogsPage = lazy(() => import("./pages/AuditPages").then((module) => ({ default: module.AccountChangeLogsPage })));
const AboutPage = lazy(() => import("./pages/AboutPage").then((module) => ({ default: module.AboutPage })));
const ClustersPage = lazy(() => import("./pages/ClustersPage").then((module) => ({ default: module.ClustersPage })));
const AccountClassificationsPage = lazy(() => import("./pages/ClassificationPages").then((module) => ({ default: module.AccountClassificationsPage })));
const ClassificationStatisticsPage = lazy(() => import("./pages/ClassificationPages").then((module) => ({ default: module.ClassificationStatisticsPage })));
const SchedulerPage = lazy(() => import("./pages/SchedulerPage").then((module) => ({ default: module.SchedulerPage })));
const SyncSessionsPage = lazy(() => import("./pages/SyncSessionsPage").then((module) => ({ default: module.SyncSessionsPage })));
const UsersPage = lazy(() => import("./pages/CatalogAdminPages").then((module) => ({ default: module.UsersPage })));
const SettingsPage = lazy(() => import("./pages/SettingsPage").then((module) => ({ default: module.SettingsPage })));
const CredentialsPage = lazy(() => import("./pages/CatalogAdminPages").then((module) => ({ default: module.CredentialsPage })));
const TagsPage = lazy(() => import("./pages/CatalogAdminPages").then((module) => ({ default: module.TagsPage })));
const PartitionsPage = lazy(() => import("./pages/PartitionsPage").then((module) => ({ default: module.PartitionsPage })));
const PlaceholderPage = lazy(() => import("./pages/PlaceholderPage").then((module) => ({ default: module.PlaceholderPage })));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false
    }
  }
});

const migratedConsolePaths = [
  "/dashboard",
  "/risk-center",
  "/instances",
  "/database-ledgers",
  "/account-ledgers",
  "/capacity/instances",
  "/capacity/databases",
  "/instance-statistics",
  "/account-statistics",
  "/database-statistics",
  "/logs",
  "/account-change-logs",
  "/clusters",
  "/account-classifications",
  "/classification-statistics",
  "/scheduler",
  "/sync-sessions",
  "/users",
  "/settings",
  "/credentials",
  "/tags",
  "/partitions"
];

function resolveErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "操作失败";
}

function ConsoleRoutes() {
  const sessionQuery = useSession();
  const loginMutation = useLogin();
  const logoutMutation = useLogout();

  const session = sessionQuery.data;
  const visibleGroups = useMemo(
    () => filterNavigationForRole(navigationGroups, session?.user?.role ?? ""),
    [session?.user?.role]
  );
  const visibleItems = useMemo(() => flattenNavigationItems(visibleGroups), [visibleGroups]);

  if (sessionQuery.isLoading) {
    return <div className="console-boot">正在加载控制台</div>;
  }

  if (!session?.authenticated || !session.user) {
    return (
      <LoginPage
        errorMessage={loginMutation.error ? resolveErrorMessage(loginMutation.error) : undefined}
        onLogin={async (payload) => {
          await loginMutation.mutateAsync(payload);
        }}
      />
    );
  }

  return (
    <BrowserRouter basename="/console">
      <AppShell
        navigationGroups={visibleGroups}
        user={session.user}
        onLogout={() => {
          logoutMutation.mutate();
        }}
      >
        <Suspense fallback={<div className="console-boot">正在加载页面</div>}>
          <Routes>
            <Route element={<Navigate to="/dashboard" replace />} path="/" />
            <Route element={<DashboardPage />} path="/dashboard" />
            <Route element={<RiskCenterPage />} path="/risk-center" />
            <Route element={<InstancesPage />} path="/instances" />
            <Route element={<InstanceDetailPage />} path="/instances/:instanceId" />
            <Route element={<DatabaseLedgersPage />} path="/database-ledgers" />
            <Route element={<AccountLedgersPage />} path="/account-ledgers" />
            <Route element={<CapacityInstancesPage />} path="/capacity/instances" />
            <Route element={<CapacityDatabasesPage />} path="/capacity/databases" />
            <Route element={<InstanceStatisticsPage />} path="/instance-statistics" />
            <Route element={<AccountStatisticsPage />} path="/account-statistics" />
            <Route element={<DatabaseStatisticsPage />} path="/database-statistics" />
            <Route element={<HistoryLogsPage />} path="/logs" />
            <Route element={<AccountChangeLogsPage />} path="/account-change-logs" />
            <Route element={<AboutPage />} path="/about" />
            <Route element={<ClustersPage />} path="/clusters" />
            <Route element={<AccountClassificationsPage currentUser={session.user} />} path="/account-classifications" />
            <Route element={<ClassificationStatisticsPage />} path="/classification-statistics" />
            <Route element={<SchedulerPage />} path="/scheduler" />
            <Route element={<SyncSessionsPage />} path="/sync-sessions" />
            <Route element={<UsersPage currentUser={session.user} />} path="/users" />
            <Route element={<SettingsPage />} path="/settings" />
            <Route element={<CredentialsPage currentUser={session.user} />} path="/credentials" />
            <Route element={<TagsPage currentUser={session.user} />} path="/tags" />
            <Route element={<PartitionsPage />} path="/partitions" />
            {visibleItems
              .filter((item) => !migratedConsolePaths.includes(item.consolePath))
              .map((item) => (
                <Route
                  element={
                    <PlaceholderPage
                      description={item.description}
                      label={item.label}
                      legacyHref={item.legacyHref}
                    />
                  }
                  key={item.consolePath}
                  path={item.consolePath}
                />
              ))}
            <Route element={<Navigate to="/dashboard" replace />} path="*" />
          </Routes>
        </Suspense>
      </AppShell>
    </BrowserRouter>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <ConsoleRoutes />
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}
