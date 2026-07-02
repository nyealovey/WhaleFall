type SnapshotRecord = Record<string, unknown>;

export type AuditTargetRow = {
  name: string;
  status: "启用" | "停用";
  enabled: boolean;
  targetType: string;
  targetSummary: string[];
  failurePolicy: string;
  updatedAt: string;
};

export type AuditSpecRow = {
  scopeLabel: "SERVER" | "DATABASE";
  scopeDetail: string;
  name: string;
  boundAudit: string;
  status: "启用" | "停用";
  enabled: boolean;
  actionCount: number;
  actionPreview: string[];
};

function text(value: unknown, fallback = "-"): string {
  if (value === null || value === undefined) {
    return fallback;
  }
  const resolved = String(value).trim();
  return resolved || fallback;
}

function bool(value: unknown): boolean {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") {
    return value !== 0;
  }
  return false;
}

function number(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return undefined;
}

function formatAuditTimestamp(value: unknown): string {
  const resolved = text(value);
  if (resolved === "-") {
    return resolved;
  }
  return resolved.split("+")[0]?.replace("T", " ") ?? resolved;
}

function actionPreview(actions: unknown): string[] {
  if (!Array.isArray(actions)) {
    return [];
  }
  return actions
    .map((item) => (item && typeof item === "object" ? (item as SnapshotRecord) : {}))
    .map((item) => text(item.display_text ?? item.name, ""))
    .filter(Boolean);
}

export function buildAuditTargetRows(records: SnapshotRecord[]): AuditTargetRow[] {
  return records.map((item) => {
    const enabled = bool(item.enabled);
    const queueDelay = number(item.queue_delay);
    const summary = [text(item.target_summary ?? item.file_path ?? item.target_type)];
    if (queueDelay !== undefined) {
      summary.push(`Queue delay: ${queueDelay} ms`);
    }

    return {
      name: text(item.name),
      status: enabled ? "启用" : "停用",
      enabled,
      targetType: text(item.target_type),
      targetSummary: summary,
      failurePolicy: text(item.on_failure),
      updatedAt: formatAuditTimestamp(item.updated_at)
    };
  });
}

export function buildAuditSpecRows(records: SnapshotRecord[]): AuditSpecRow[] {
  return records.map((item) => {
    const scopeLabel = text(item.scope).toLowerCase() === "database" ? "DATABASE" : "SERVER";
    const enabled = bool(item.enabled);
    const preview = actionPreview(item.actions);
    return {
      scopeLabel,
      scopeDetail: scopeLabel === "DATABASE" ? text(item.database_name) : "实例级",
      name: text(item.name),
      boundAudit: text(item.audit_name),
      status: enabled ? "启用" : "停用",
      enabled,
      actionCount: number(item.action_count) ?? preview.length,
      actionPreview: preview
    };
  });
}
