import type { HistoryLogItem } from "@/api/audit";

export function historyLogLevelLabel(log: Pick<HistoryLogItem, "level" | "level_label">): string {
  return log.level_label || log.level || "-";
}

export function historyLogModuleLabel(log: Pick<HistoryLogItem, "module" | "module_label">): string {
  return log.module_label || log.module || "-";
}

export function historyLogMessageLabel(log: Pick<HistoryLogItem, "message" | "message_label">): string {
  return log.message_label || log.message || "-";
}
