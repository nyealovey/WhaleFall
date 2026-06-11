import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useMemo } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ApiError } from "./api/client";
import { useLogin, useLogout, useSession } from "./auth/useSession";
import { AppShell } from "./layout/AppShell";
import { filterNavigationForRole, flattenNavigationItems, navigationGroups } from "./navigation";
import { AccountChangeLogsPage, HistoryLogsPage } from "./pages/AuditPages";
import { CapacityDatabasesPage, CapacityInstancesPage } from "./pages/CapacityPages";
import { DashboardPage } from "./pages/DashboardPage";
import { AccountLedgersPage, DatabaseLedgersPage, InstancesPage } from "./pages/ListPages";
import { LoginPage } from "./pages/LoginPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { RiskCenterPage } from "./pages/RiskCenterPage";
import { AccountStatisticsPage, DatabaseStatisticsPage, InstanceStatisticsPage } from "./pages/StatisticsPages";

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
  "/account-change-logs"
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
        <Routes>
          <Route element={<Navigate to="/dashboard" replace />} path="/" />
          <Route element={<DashboardPage />} path="/dashboard" />
          <Route element={<RiskCenterPage />} path="/risk-center" />
          <Route element={<InstancesPage />} path="/instances" />
          <Route element={<DatabaseLedgersPage />} path="/database-ledgers" />
          <Route element={<AccountLedgersPage />} path="/account-ledgers" />
          <Route element={<CapacityInstancesPage />} path="/capacity/instances" />
          <Route element={<CapacityDatabasesPage />} path="/capacity/databases" />
          <Route element={<InstanceStatisticsPage />} path="/instance-statistics" />
          <Route element={<AccountStatisticsPage />} path="/account-statistics" />
          <Route element={<DatabaseStatisticsPage />} path="/database-statistics" />
          <Route element={<HistoryLogsPage />} path="/logs" />
          <Route element={<AccountChangeLogsPage />} path="/account-change-logs" />
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
      </AppShell>
    </BrowserRouter>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConsoleRoutes />
    </QueryClientProvider>
  );
}
