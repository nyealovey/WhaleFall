import { apiClient, type ApiClient } from "./client";

type ApiReader = Pick<ApiClient, "get">;

export type RiskSeverity = "high" | "medium" | "low" | "ok" | string;

export type RiskCenterSummary = {
  total_instances: number;
  severity_counts: Record<string, number>;
  db_type_counts: Record<string, { total: number; high: number; medium: number; low: number; ok: number }>;
  top_risks: Array<{
    rule_key: string;
    instance_name: string;
    severity: RiskSeverity;
    label?: string;
    detail?: string;
  }>;
  generated_at: string;
};

export type RiskCenterCard = {
  instance_id: number;
  name: string;
  db_type: string;
  host: string;
  port: number;
  overall_severity: RiskSeverity;
  risk_score: number;
  risk_flags?: string[];
  risk_items?: Array<{
    rule_key: string;
    category: string;
    severity: RiskSeverity;
    label: string;
    detail: string;
    target_url?: string | null;
  }>;
  status_band?: string;
  group?: string;
  backup?: Record<string, unknown>;
  audit?: Record<string, unknown>;
  managed?: Record<string, unknown>;
  cluster?: Record<string, unknown>;
  capacity?: Record<string, unknown>;
  access?: Record<string, unknown>;
  tasks?: Record<string, unknown>;
  links?: Record<string, string>;
};

export type RiskCenterCardsResponse = {
  items: RiskCenterCard[];
  total: number;
  page: number;
  pages: number;
  limit: number;
};

export type RiskCenterSnapshot = {
  summary: RiskCenterSummary;
  cards: RiskCenterCardsResponse;
};

export type RiskCenterFilters = {
  dbType?: string;
  limit?: number;
  page?: number;
  search?: string;
  severity?: string;
  status?: string;
  tag?: string;
};

function riskCardsPath(filters: RiskCenterFilters): string {
  const params = new URLSearchParams();
  params.set("limit", String(filters.limit ?? 12));
  if (filters.page) {
    params.set("page", String(filters.page));
  }
  if (filters.severity) {
    params.set("severity", filters.severity);
  }
  if (filters.dbType) {
    params.set("db_type", filters.dbType);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.tag) {
    params.set("tag", filters.tag);
  }
  if (filters.search) {
    params.set("search", filters.search);
  }
  return `/api/v1/risk-center/cards?${params.toString()}`;
}

export async function fetchRiskCenterSnapshot(
  filters: RiskCenterFilters = {},
  client: ApiReader = apiClient
): Promise<RiskCenterSnapshot> {
  const [summary, cards] = await Promise.all([
    client.get<RiskCenterSummary>("/api/v1/risk-center/summary"),
    client.get<RiskCenterCardsResponse>(riskCardsPath(filters))
  ]);

  return {
    summary,
    cards
  };
}
