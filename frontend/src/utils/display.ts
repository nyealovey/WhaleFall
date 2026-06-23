const DATABASE_TYPE_LABELS: Record<string, string> = {
  mysql: "MySQL",
  oracle: "Oracle",
  postgresql: "PostgreSQL",
  sqlserver: "SQL Server"
};

const STATUS_LABELS: Record<string, string> = {
  active: "启用",
  cancelled: "已取消",
  completed: "已完成",
  completed_with_errors: "部分完成",
  disabled: "停用",
  failed: "失败",
  healthy: "正常",
  inactive: "停用",
  pending: "等待中",
  running: "运行中",
  success: "成功",
  unknown: "未知",
  warning: "警告"
};

export function formatCapacityMb(value: number | null | undefined): string {
  const megabytes = value ?? 0;
  if (Math.abs(megabytes) >= 1024 * 1024) {
    return `${(megabytes / (1024 * 1024)).toFixed(2)} TB`;
  }
  if (Math.abs(megabytes) >= 1024) {
    return `${(megabytes / 1024).toFixed(2)} GB`;
  }
  return `${megabytes.toFixed(0)} MB`;
}

export function formatDatabaseType(value: string | null | undefined): string {
  if (!value) return "-";
  return DATABASE_TYPE_LABELS[value.toLowerCase()] ?? value;
}

export function formatStatus(value: string | boolean | null | undefined): string {
  if (typeof value === "boolean") return value ? "启用" : "停用";
  if (!value) return "-";
  return STATUS_LABELS[value.toLowerCase()] ?? value;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}
