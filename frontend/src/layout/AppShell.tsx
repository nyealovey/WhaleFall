import { KeyRound, LogOut } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/utils/cn";

import type { NavigationGroup } from "../navigation";
import type { SessionUser } from "../types/auth";

type AppShellProps = {
  navigationGroups: NavigationGroup[];
  user: SessionUser;
  onLogout: () => void;
  children: ReactNode;
};

const APP_VERSION = "1.5.0";

export function AppShell({ navigationGroups, user, onLogout, children }: AppShellProps) {
  return (
    <div className="grid min-h-dvh grid-cols-[15.75rem_minmax(0,1fr)] bg-background max-lg:grid-cols-1">
      <aside className="sticky top-0 h-dvh overflow-y-auto border-r bg-sidebar text-sidebar-foreground max-lg:static max-lg:h-auto" aria-label="主导航">
        <a className="flex min-h-18 items-center gap-3 px-4 py-3 no-underline" href="/console/dashboard">
          <img className="rounded-md" src="/static/img/logo.webp" alt="鲸落" width="40" height="40" />
          <span>
            <strong className="font-display block text-[1.35rem] leading-none">鲸落</strong>
            <small className="font-mono text-xs tracking-[0.06em] text-muted-foreground uppercase">OPS CONSOLE</small>
          </span>
        </a>

        <nav className="grid gap-3 px-3 pb-4 max-lg:grid-cols-2 max-sm:grid-cols-1" aria-label="React 控制台导航">
          {navigationGroups.map((group) => (
            <section className="grid gap-1" key={group.label}>
              <h2 className="font-mono mt-2 px-2 text-xs tracking-[0.06em] text-muted-foreground uppercase">
                {group.label}
              </h2>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    className={({ isActive }) =>
                      cn(
                        "flex min-h-9 items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-sm text-sidebar-foreground/85 no-underline transition-colors hover:border-sidebar-border hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:outline-none",
                        isActive &&
                          "border-sidebar-border bg-sidebar-accent text-sidebar-accent-foreground shadow-xs"
                      )
                    }
                    key={item.consolePath}
                    to={item.consolePath}
                  >
                    <Icon className="size-4 shrink-0" aria-hidden />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </section>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="flex min-h-[var(--topbar-height)] items-center justify-end gap-3 border-b bg-muted px-5 max-sm:justify-between" role="banner">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="outline">React preview</Badge>
            <strong>{user.username}</strong>
            <Separator className="h-4 w-px" />
            <span>{user.role}</span>
          </div>
          <Button variant="outline" size="sm" asChild>
            <a href="/auth/change-password">
              <KeyRound aria-hidden size={16} />
              <span>修改密码</span>
            </a>
          </Button>
          <Button variant="outline" size="sm" type="button" onClick={onLogout}>
            <LogOut aria-hidden size={16} />
            <span>退出</span>
          </Button>
        </header>
        <div className="min-w-0 flex-1">{children}</div>
        <footer className="border-t bg-muted px-5 py-3 text-sm text-muted-foreground" role="contentinfo">
          <p className="mb-0 flex flex-wrap items-center justify-center gap-1.5">
            <span>&copy; {new Date().getFullYear()}</span>
            <span>鲸落</span>
            <span>{APP_VERSION}</span>
            <span>-</span>
            <span>数据同步管理平台</span>
            <span>|</span>
            <a className="font-medium text-foreground underline-offset-4 hover:underline" href="/console/about">
              关于
            </a>
          </p>
        </footer>
      </div>
    </div>
  );
}
