import { apiClient, type ApiClient } from "./client";

type ApiActionClient = Pick<ApiClient, "delete" | "patch" | "post" | "put">;
const DEFAULT_LIST_LIMIT = 200;

export type RiskRulePayload = {
  rule_key: string;
  enabled: boolean;
  severity: string;
};

export type UserWritePayload = {
  username: string;
  role: string;
  password?: string;
  is_active: boolean;
};

export type CredentialWritePayload = {
  name: string;
  credential_type: string;
  db_type?: string | null;
  username: string;
  password?: string;
  description?: string | null;
  is_active: boolean;
};

export type TagWritePayload = {
  name: string;
  display_name: string;
  category: string;
  is_active: boolean;
};

export type AccountClassificationWritePayload = {
  code?: string;
  display_name: string;
  description?: string | null;
  risk_level?: number;
  icon_name?: string | null;
  priority?: number;
};

export type AccountClassificationRuleWritePayload = {
  rule_name: string;
  classification_id: number;
  db_type: string;
  operator: string;
  rule_expression?: unknown;
  is_active?: boolean;
};

export type SchedulerJobWritePayload = {
  trigger_type: string;
  cron_expression: string;
};

export type JumpServerSourcePayload = {
  credential_id: number;
  base_url: string;
  org_id?: string | null;
  verify_ssl?: boolean | null;
};

export type VeeamSourcePayload = {
  name?: string | null;
  credential_id: number;
  server_host: string;
  server_port: number;
  api_version: string;
  verify_ssl?: boolean | null;
  match_domains?: string[];
};

export type AdDomainConfigPayload = {
  name: string;
  netbios_name: string;
  domain_controllers: string[];
  ldap_port: number;
  use_ssl: boolean;
  verify_ssl?: boolean | null;
  base_dn: string;
  credential_id: number;
  is_enabled: boolean;
  description?: string | null;
};

export type SqlServerClusterPayload = {
  name: string;
  domain_name: string;
  description?: string | null;
  is_enabled: boolean;
};

export type MySqlClusterPayload = {
  name: string;
  description?: string | null;
  is_enabled: boolean;
};

export type InstanceWritePayload = {
  name: string;
  db_type: string;
  host: string;
  port: number;
  database_name?: string | null;
  credential_id?: number | null;
  description?: string | null;
  tag_names?: string[];
  is_active: boolean;
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

export function createAccountClassification(payload: AccountClassificationWritePayload, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/accounts/classifications", payload);
}

export function updateAccountClassification(
  classificationId: number,
  payload: AccountClassificationWritePayload,
  client: ApiActionClient = apiClient
) {
  return client.put(`/api/v1/accounts/classifications/${classificationId}`, payload);
}

export function deleteAccountClassificationRule(ruleId: number, client: ApiActionClient = apiClient) {
  return client.delete(`/api/v1/accounts/classifications/rules/${ruleId}`);
}

export function createAccountClassificationRule(payload: AccountClassificationRuleWritePayload, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/accounts/classifications/rules", payload);
}

export function updateAccountClassificationRule(
  ruleId: number,
  payload: AccountClassificationRuleWritePayload,
  client: ApiActionClient = apiClient
) {
  return client.put(`/api/v1/accounts/classifications/rules/${ruleId}`, payload);
}

export function validateAccountClassificationRuleExpression(ruleExpression: unknown, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/accounts/classifications/rules/actions/validate-expression", {
    rule_expression: ruleExpression
  });
}

export function createUser(payload: UserWritePayload & { password: string }, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/users", payload);
}

export function updateUser(userId: number, payload: UserWritePayload, client: ApiActionClient = apiClient) {
  return client.put(`/api/v1/users/${userId}`, payload);
}

export function deleteUser(userId: number, client: ApiActionClient = apiClient) {
  return client.delete(`/api/v1/users/${userId}`);
}

export function createCredential(payload: CredentialWritePayload & { password: string }, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/credentials", payload);
}

export function updateCredential(credentialId: number, payload: CredentialWritePayload, client: ApiActionClient = apiClient) {
  return client.put(`/api/v1/credentials/${credentialId}`, payload);
}

export function deleteCredential(credentialId: number, client: ApiActionClient = apiClient) {
  return client.delete(`/api/v1/credentials/${credentialId}`);
}

export function createTag(payload: TagWritePayload, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/tags", payload);
}

export function updateTag(tagId: number, payload: TagWritePayload, client: ApiActionClient = apiClient) {
  return client.put(`/api/v1/tags/${tagId}`, payload);
}

export function deleteTag(tagId: number, client: ApiActionClient = apiClient) {
  return client.delete(`/api/v1/tags/${tagId}`);
}

export function assignTagsToInstances(instanceIds: number[], tagIds: number[], client: ApiActionClient = apiClient) {
  return client.post("/api/v1/tags/bulk/actions/assign", { instance_ids: instanceIds, tag_ids: tagIds });
}

export function removeTagsFromInstances(instanceIds: number[], tagIds: number[], client: ApiActionClient = apiClient) {
  return client.post("/api/v1/tags/bulk/actions/remove", { instance_ids: instanceIds, tag_ids: tagIds });
}

export function removeAllTagsFromInstances(instanceIds: number[], client: ApiActionClient = apiClient) {
  return client.post("/api/v1/tags/bulk/actions/remove-all", { instance_ids: instanceIds });
}

export function syncDatabases(client: ApiActionClient = apiClient) {
  return client.post("/api/v1/databases/ledgers/actions/sync-all", {});
}

export function syncAccounts(client: ApiActionClient = apiClient) {
  return client.post("/api/v1/instances/actions/sync-accounts", {});
}

export function createSqlServerCluster(payload: SqlServerClusterPayload, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/sqlserver-clusters", payload);
}

export function updateSqlServerCluster(clusterId: number, payload: SqlServerClusterPayload, client: ApiActionClient = apiClient) {
  return client.patch(`/api/v1/sqlserver-clusters/${clusterId}`, payload);
}

export function syncSqlServerAvailabilityGroups(
  clusterId: number,
  connectionDatabase = "master",
  client: ApiActionClient = apiClient
) {
  return client.post(`/api/v1/sqlserver-clusters/${clusterId}/availability-groups/actions/sync`, {
    connection_database: connectionDatabase
  });
}

export function syncSqlServerClusterStatus(clusterId: number, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/sqlserver-clusters/${clusterId}/actions/sync-status`, {});
}

export function syncSqlServerAgAccounts(clusterId: number, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/sqlserver-clusters/${clusterId}/availability-groups/actions/sync-accounts`, {});
}

export function createMySqlCluster(payload: MySqlClusterPayload, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/mysql-clusters", payload);
}

export function updateMySqlCluster(clusterId: number, payload: MySqlClusterPayload, client: ApiActionClient = apiClient) {
  return client.patch(`/api/v1/mysql-clusters/${clusterId}`, payload);
}

export function syncMySqlClusterTopology(clusterId: number, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/mysql-clusters/${clusterId}/actions/sync-topology`, {});
}

export function createInstance(payload: InstanceWritePayload, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/instances", payload);
}

export function updateInstance(instanceId: number, payload: InstanceWritePayload, client: ApiActionClient = apiClient) {
  return client.put(`/api/v1/instances/${instanceId}`, payload);
}

export function testInstanceConnection(instanceId: number, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/instances/actions/test-connection", { instance_id: instanceId });
}

export function batchTestInstanceConnections(instanceIds: number[], client: ApiActionClient = apiClient) {
  return client.post("/api/v1/instances/actions/batch-test-connections", { instance_ids: instanceIds });
}

export function deleteInstance(instanceId: number, client: ApiActionClient = apiClient) {
  return client.delete(`/api/v1/instances/${instanceId}`);
}

export function restoreInstance(instanceId: number, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/instances/${instanceId}/actions/restore`, {});
}

export function refreshDatabaseTableSizes(databaseId: number, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/databases/${databaseId}/tables/sizes/actions/refresh?page=1&limit=${DEFAULT_LIST_LIMIT}`, {});
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

export function updateSchedulerJob(jobId: string, payload: SchedulerJobWritePayload, client: ApiActionClient = apiClient) {
  return client.put(`/api/v1/scheduler/jobs/${encodeURIComponent(jobId)}`, payload);
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

export function saveJumpServerSource(payload: JumpServerSourcePayload, client: ApiActionClient = apiClient) {
  return client.put("/api/v1/integrations/jumpserver/source", payload);
}

export function unbindJumpServer(client: ApiActionClient = apiClient) {
  return client.delete("/api/v1/integrations/jumpserver/source");
}

export function syncVeeam(client: ApiActionClient = apiClient) {
  return client.post("/api/v1/integrations/veeam/actions/sync", {});
}

export function createVeeamSource(payload: VeeamSourcePayload, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/integrations/veeam/sources", payload);
}

export function updateVeeamSource(sourceId: number, payload: VeeamSourcePayload, client: ApiActionClient = apiClient) {
  return client.put(`/api/v1/integrations/veeam/sources/${sourceId}`, payload);
}

export function enableVeeamSource(sourceId: number, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/integrations/veeam/sources/${sourceId}/actions/enable`, {});
}

export function disableVeeamSource(sourceId: number, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/integrations/veeam/sources/${sourceId}/actions/disable`, {});
}

export function deleteVeeamSource(sourceId: number, client: ApiActionClient = apiClient) {
  return client.delete(`/api/v1/integrations/veeam/sources/${sourceId}`);
}

export function syncAdDomains(client: ApiActionClient = apiClient) {
  return client.post("/api/v1/ad-domain-configs/actions/sync", {});
}

export function createAdDomainConfig(payload: AdDomainConfigPayload, client: ApiActionClient = apiClient) {
  return client.post("/api/v1/ad-domain-configs", payload);
}

export function updateAdDomainConfig(configId: number, payload: AdDomainConfigPayload, client: ApiActionClient = apiClient) {
  return client.put(`/api/v1/ad-domain-configs/${configId}`, payload);
}

export function setAdDomainConfigEnabled(configId: number, isEnabled: boolean, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/ad-domain-configs/${configId}/actions/set-enabled`, { is_enabled: isEnabled });
}

export function testAdDomainConfig(configId: number, client: ApiActionClient = apiClient) {
  return client.post(`/api/v1/ad-domain-configs/${configId}/actions/test-connection`, {});
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
