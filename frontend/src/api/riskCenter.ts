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

export async function fetchRiskCenterSnapshot(client: ApiReader = apiClient): Promise<RiskCenterSnapshot> {
  const [summary, cards] = await Promise.all([
    client.get<RiskCenterSummary>("/api/v1/risk-center/summary"),
    client.get<RiskCenterCardsResponse>("/api/v1/risk-center/cards?limit=12")
  ]);

  return {
    summary,
    cards
  };
}
