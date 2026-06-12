import { describe, expect, it, vi } from "vitest";

import {
  cancelSyncSession,
  cleanupPartitions,
  createPartition,
  deleteAccountClassification,
  deleteAccountClassificationRule,
  deleteAdDomainConfig,
  deleteVeeamSource,
  pauseSchedulerJob,
  reloadSchedulerJobs,
  resumeSchedulerJob,
  runSchedulerJob,
  saveAlertSettings,
  saveRiskRules,
  sendAlertTestEmail,
  sendFeishuTest,
  syncAccounts,
  syncAdDomains,
  syncDatabases,
  syncJumpServer,
  syncVeeam,
  testInstanceConnection,
  triggerCapacityAggregation,
  autoClassifyAccounts,
  unbindJumpServer
} from "./actions";

describe("console action api", () => {
  it("posts direct operational actions to their v1 endpoints", async () => {
    const client = {
      post: vi.fn().mockResolvedValue({ ok: true }),
      put: vi.fn().mockResolvedValue({ ok: true }),
      delete: vi.fn().mockResolvedValue({ ok: true })
    };

    await triggerCapacityAggregation("database", client);
    await autoClassifyAccounts(client);
    await syncDatabases(client);
    await syncAccounts(client);
    await testInstanceConnection(7, client);
    await reloadSchedulerJobs(client);
    await pauseSchedulerJob("job-1", client);
    await resumeSchedulerJob("job-1", client);
    await runSchedulerJob("job-1", client);
    await cancelSyncSession("s-1", client);
    await sendAlertTestEmail(["ops@example.com"], client);
    await sendFeishuTest("https://bot.example", client);
    await saveAlertSettings({ global_enabled: true }, client);
    await saveRiskRules([{ rule_key: "backup_issue", enabled: true, severity: "high" }], client);
    await syncJumpServer(client);
    await unbindJumpServer(client);
    await syncVeeam(client);
    await deleteVeeamSource(9, client);
    await syncAdDomains(client);
    await deleteAdDomainConfig(1, client);
    await createPartition(undefined, client);
    await cleanupPartitions(12, client);
    await deleteAccountClassification(5, client);
    await deleteAccountClassificationRule(6, client);

    expect(client.post).toHaveBeenCalledWith("/api/v1/capacity/aggregations/current", { scope: "database" });
    expect(client.post).toHaveBeenCalledWith("/api/v1/accounts/classifications/actions/auto-classify", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/databases/ledgers/actions/sync-all", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/instances/actions/sync-accounts", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/instances/actions/test-connection", { instance_id: 7 });
    expect(client.post).toHaveBeenCalledWith("/api/v1/scheduler/jobs/actions/reload", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/scheduler/jobs/job-1/actions/pause", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/scheduler/jobs/job-1/actions/resume", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/scheduler/jobs/job-1/actions/run", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/sync-sessions/s-1/actions/cancel", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/alerts/email-settings/actions/send-test", { recipients: ["ops@example.com"] });
    expect(client.post).toHaveBeenCalledWith("/api/v1/alerts/email-settings/actions/send-feishu-test", { feishu_webhook_url: "https://bot.example" });
    expect(client.put).toHaveBeenCalledWith("/api/v1/alerts/email-settings", { global_enabled: true });
    expect(client.put).toHaveBeenCalledWith("/api/v1/risk-center/rules", {
      rules: [{ rule_key: "backup_issue", enabled: true, severity: "high" }]
    });
    expect(client.post).toHaveBeenCalledWith("/api/v1/integrations/jumpserver/actions/sync", {});
    expect(client.delete).toHaveBeenCalledWith("/api/v1/integrations/jumpserver/source");
    expect(client.post).toHaveBeenCalledWith("/api/v1/integrations/veeam/actions/sync", {});
    expect(client.delete).toHaveBeenCalledWith("/api/v1/integrations/veeam/sources/9");
    expect(client.post).toHaveBeenCalledWith("/api/v1/ad-domain-configs/actions/sync", {});
    expect(client.delete).toHaveBeenCalledWith("/api/v1/ad-domain-configs/1");
    expect(client.post).toHaveBeenCalledWith("/api/v1/partitions", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/partitions/actions/cleanup", { retention_months: 12 });
    expect(client.delete).toHaveBeenCalledWith("/api/v1/accounts/classifications/5");
    expect(client.delete).toHaveBeenCalledWith("/api/v1/accounts/classifications/rules/6");
  });
});
