import { Crown, Database, Globe2, KeyRound, ShieldCheck, UserCheck, UserCog, Users, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";

type PermissionCategories = Record<string, unknown>;
type PermissionMapEntry = {
  label: string;
  values: string[];
};
type PermissionSection =
  | {
      color: "blue" | "green" | "orange" | "red" | "sky";
      emptyLabel: string;
      icon: LucideIcon;
      mode: "list";
      source: string;
      title: string;
    }
  | {
      color: "blue" | "green" | "orange" | "red" | "sky";
      emptyLabel: string;
      icon: LucideIcon;
      mode: "nestedList";
      parent: string;
      source: string;
      title: string;
    }
  | {
      color: "blue" | "green" | "orange" | "red" | "sky";
      emptyLabel: string;
      icon: LucideIcon;
      mode: "map";
      source: string;
      title: string;
    }
  ;

const COLOR_CLASSES: Record<PermissionSection["color"], string> = {
  blue: "border-blue-200 bg-blue-50 text-blue-800",
  green: "border-emerald-200 bg-emerald-50 text-emerald-800",
  orange: "border-orange-200 bg-orange-50 text-orange-800",
  red: "border-red-200 bg-red-50 text-red-800",
  sky: "border-sky-200 bg-sky-50 text-sky-800"
};

const SECTIONS_BY_DB_TYPE: Record<string, PermissionSection[]> = {
  mysql: [
    { title: "直授角色", icon: UserCog, color: "sky", mode: "nestedList", parent: "mysql_granted_roles", source: "direct", emptyLabel: "无直授角色" },
    { title: "默认角色", icon: UserCheck, color: "green", mode: "nestedList", parent: "mysql_granted_roles", source: "default", emptyLabel: "无默认角色" },
    { title: "直授用户", icon: Users, color: "blue", mode: "nestedList", parent: "mysql_role_members", source: "direct", emptyLabel: "无直授用户" },
    { title: "默认用户", icon: Users, color: "blue", mode: "nestedList", parent: "mysql_role_members", source: "default", emptyLabel: "无默认用户" },
    { title: "全局权限", icon: Globe2, color: "orange", mode: "list", source: "mysql_global_privileges", emptyLabel: "无全局权限" },
    { title: "数据库权限", icon: Database, color: "green", mode: "map", source: "mysql_database_privileges", emptyLabel: "无数据库权限" }
  ],
  postgresql: [
    { title: "预定义角色", icon: UserCog, color: "sky", mode: "list", source: "postgresql_predefined_roles", emptyLabel: "无预定义角色" },
    { title: "角色属性", icon: ShieldCheck, color: "orange", mode: "list", source: "postgresql_role_attributes", emptyLabel: "无角色属性" },
    { title: "数据库权限", icon: Database, color: "green", mode: "map", source: "postgresql_database_privileges", emptyLabel: "无数据库权限" }
  ],
  oracle: [
    { title: "角色", icon: Crown, color: "orange", mode: "list", source: "oracle_roles", emptyLabel: "无角色" },
    { title: "系统权限", icon: ShieldCheck, color: "red", mode: "list", source: "oracle_system_privileges", emptyLabel: "无系统权限" }
  ],
  sqlserver: [
    { title: "服务器角色", icon: Crown, color: "orange", mode: "list", source: "sqlserver_server_roles", emptyLabel: "无服务器角色" },
    { title: "数据库角色", icon: Database, color: "green", mode: "map", source: "sqlserver_database_roles", emptyLabel: "无数据库角色" },
    { title: "服务器权限", icon: ShieldCheck, color: "red", mode: "list", source: "sqlserver_server_permissions", emptyLabel: "无服务器权限" },
    { title: "数据库权限", icon: KeyRound, color: "blue", mode: "map", source: "sqlserver_database_permissions", emptyLabel: "无数据库权限" }
  ]
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function extractCategories(snapshot: unknown): PermissionCategories | undefined {
  if (!isRecord(snapshot) || !isRecord(snapshot.categories)) {
    return undefined;
  }
  return snapshot.categories;
}

function asStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return [...new Set(value.map((item) => String(item).trim()).filter(Boolean))];
  }
  if (isRecord(value)) {
    const databaseValues = value.database;
    if (Array.isArray(databaseValues)) {
      return asStringList(databaseValues);
    }
    return Object.entries(value)
      .filter(([, enabled]) => enabled === true)
      .map(([key]) => key);
  }
  return [];
}

function nestedList(categories: PermissionCategories, parent: string, source: string): string[] {
  const parentValue = categories[parent];
  return isRecord(parentValue) ? asStringList(parentValue[source]) : [];
}

function asStringMap(value: unknown): PermissionMapEntry[] {
  if (!isRecord(value)) {
    return [];
  }
  return Object.entries(value).map(([label, rawValue]) => ({ label, values: asStringList(rawValue) }));
}

function sectionContent(categories: PermissionCategories, section: PermissionSection) {
  switch (section.mode) {
    case "list":
      return renderChips(asStringList(categories[section.source]), section.emptyLabel);
    case "nestedList":
      return renderChips(nestedList(categories, section.parent, section.source), section.emptyLabel);
    case "map":
      return renderRows(asStringMap(categories[section.source]), section.emptyLabel);
  }
}

function renderChips(values: string[], emptyLabel: string) {
  if (values.length === 0) {
    return (
      <Badge className="w-fit rounded-full px-3 py-1 text-sm text-muted-foreground" variant="secondary">
        {emptyLabel}
      </Badge>
    );
  }
  return (
    <div className="flex flex-wrap gap-2">
      {values.map((value) => (
        <Badge className="rounded-full px-3 py-1 text-sm" key={value} variant="outline">
          {value}
        </Badge>
      ))}
    </div>
  );
}

function renderRows(rows: PermissionMapEntry[], emptyLabel: string) {
  if (rows.length === 0) {
    return renderChips([], emptyLabel);
  }
  return (
    <div className="grid gap-3">
      {rows.map((row) => (
        <div className="grid gap-2 rounded-md border bg-secondary/20 p-3" key={row.label}>
          <div className="text-sm font-semibold">{row.label}</div>
          {renderChips(row.values, "无权限")}
        </div>
      ))}
    </div>
  );
}

function PermissionSectionCard({ categories, section }: { categories: PermissionCategories; section: PermissionSection }) {
  const Icon = section.icon;
  return (
    <section className="grid gap-3 rounded-lg border bg-background p-4 shadow-sm">
      <div>
        <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-semibold ${COLOR_CLASSES[section.color]}`}>
          <Icon aria-hidden size={16} />
          {section.title}
        </span>
      </div>
      {sectionContent(categories, section)}
    </section>
  );
}

export function PermissionSnapshotView({ dbType, snapshot }: { dbType?: string | null; snapshot: unknown }) {
  const categories = extractCategories(snapshot);
  const sections = dbType ? SECTIONS_BY_DB_TYPE[dbType.toLowerCase()] : undefined;
  if (!categories || !sections) {
    return (
      <Badge className="w-fit rounded-full px-3 py-1 text-sm text-muted-foreground" variant="secondary">
        无权限数据
      </Badge>
    );
  }

  return (
    <div className="grid gap-3">
      {sections.map((section) => (
        <PermissionSectionCard categories={categories} key={section.title} section={section} />
      ))}
    </div>
  );
}
