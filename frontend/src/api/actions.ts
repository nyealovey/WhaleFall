import { apiClient, type ApiClient } from "./client";

type ApiActionClient = Pick<ApiClient, "delete" | "post" | "put">;

export type RiskRulePayload = {
  rule_key: string;
  enabled: boolean;
  severity: string;
};

export function triggerCapacityAggregation(scope: "instance" | "database" | "all", client: ApiActionClient = apiClient) {
  return client.post("/api/v1/capacity/aggregations/current", { scope });
}

export function autoClassifyAccounts(client: ApiActionClient = apiClient) {
  return client.post("/api/v1/accounts/classifications/actions/auto-classify", {});
}

export function deleteAccountClassification(classificationId: number, client: ApiActionClient = apiClient) {
  return client.delete(`/api/v1/accounts/classifications/${classificationId}`);
}

export function deleteAccountClassificationRule(ruleId: number, client: ApiActionClient = apiClient) {
  return client.delete(`/api/v1/accounts/classifications/rules/${ruleId}`);
}

export function syncDatabases(client: ApiActionClient = apiClient) {
  return client.post("/api/v1/databases/ledgers/actions/sync-all", {});
}

export function syncAccounts(client: ApiActionClient = apiClient) {
  return client.post("/api/v1/instances/actions/sync-accounts", {});
}

export function testInstanceConnection(instanceId: number, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/instances/actions/test-connection", { instance_id: instanceId });
}

export function reloadSchedulerJobs(client: ApiActionClient = apiClient) {
  return client.post("/api/v1/scheduler/jobs/actions/reload", {});
}

export function pauseSchedulerJob(jobId: string, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/scheduler/jobs/${encodeURIComponent(jobId)}/actions/pause`, {});
}

export function resumeSchedulerJob(jobId: string, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/scheduler/jobs/${encodeURIComponent(jobId)}/actions/resume`, {});
}

export function runSchedulerJob(jobId: string, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/scheduler/jobs/${encodeURIComponent(jobId)}/actions/run`, {});
}

export function cancelSyncSession(sessionId: string, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/sync-sessions/${encodeURIComponent(sessionId)}/actions/cancel`, {});
}

export function sendAlertTestEmail(recipients: string[], client: ApiActionClient = apiClient) {
  return client.post("/api/v1/alerts/email-settings/actions/send-test", { recipients });
}

export function sendFeishuTest(feishuWebhookUrl: string, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/alerts/email-settings/actions/send-feishu-test", { feishu_webhook_url: feishuWebhookUrl });
}

export function saveAlertSettings(settings: Record<string, unknown>, client: ApiActionClient = apiClient) {
  return client.put("/api/v1/alerts/email-settings", settings);
}

export function saveRiskRules(rules: RiskRulePayload[], client: ApiActionClient = apiClient) {
  return client.put("/api/v1/risk-center/rules", { rules });
}

export function syncJumpServer(client: ApiActionClient = apiClient) {
  return client.post("/api/v1/integrations/jumpserver/actions/sync", {});
}

export function unbindJumpServer(client: ApiActionClient = apiClient) {
  return client.delete("/api/v1/integrations/jumpserver/source");
}

export function syncVeeam(client: ApiActionClient = apiClient) {
  return client.post("/api/v1/integrations/veeam/actions/sync", {});
}

export function deleteVeeamSource(sourceId: number, client: ApiActionClient = apiClient) {
  return client.delete(`/api/v1/integrations/veeam/sources/${sourceId}`);
}

export function syncAdDomains(client: ApiActionClient = apiClient) {
  return client.post("/api/v1/ad-domain-configs/actions/sync", {});
}

export function deleteAdDomainConfig(configId: number, client: ApiActionClient = apiClient) {
  return client.delete(`/api/v1/ad-domain-configs/${configId}`);
}

export function createPartition(date: string | undefined, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/partitions", date ? { date } : {});
}

export function cleanupPartitions(retentionMonths: number, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/partitions/actions/cleanup", { retention_months: retentionMonths });
}
