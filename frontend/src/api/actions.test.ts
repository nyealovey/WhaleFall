import { describe, expect, it, vi } from "vitest";

import {
  cancelSyncSession,
  cleanupPartitions,
  createAccountClassification,
  createAccountClassificationRule,
  createInstance,
  createMySqlCluster,
  createPartition,
  createSqlServerCluster,
  createCredential,
  createTag,
  createUser,
  deleteAccountClassification,
  deleteAccountClassificationRule,
  deleteAdDomainConfig,
  deleteCredential,
  deleteInstance,
  deleteTag,
  deleteUser,
  deleteVeeamSource,
  pauseSchedulerJob,
  refreshDatabaseTableSizes,
  reloadSchedulerJobs,
  restoreInstance,
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
  syncMySqlClusterTopology,
  syncSqlServerAgAccounts,
  syncSqlServerAvailabilityGroups,
  syncSqlServerClusterStatus,
  syncVeeam,
  batchTestInstanceConnections,
  testInstanceConnection,
  triggerCapacityAggregation,
  autoClassifyAccounts,
  updateAccountClassification,
  updateAccountClassificationRule,
  updateInstance,
  updateMySqlCluster,
  updateSqlServerCluster,
  updateCredential,
  updateSchedulerJob,
  updateTag,
  updateUser,
  assignTagsToInstances,
  createAdDomainConfig,
  createVeeamSource,
  disableVeeamSource,
  enableVeeamSource,
  saveJumpServerSource,
  setAdDomainConfigEnabled,
  testAdDomainConfig,
  removeTagsFromInstances,
  removeAllTagsFromInstances,
  validateAccountClassificationRuleExpression,
  updateAdDomainConfig,
  updateVeeamSource,
  unbindJumpServer
} from "./actions";

describe("console action api", () => {
  it("posts direct operational actions to their v1 endpoints", async () => {
    const client = {
      post: vi.fn().mockResolvedValue({ ok: true }),
      patch: vi.fn().mockResolvedValue({ ok: true }),
      put: vi.fn().mockResolvedValue({ ok: true }),
      delete: vi.fn().mockResolvedValue({ ok: true })
    };

    await triggerCapacityAggregation("database", client);
    await autoClassifyAccounts(client);
    await syncDatabases(client);
    await syncAccounts(client);
    await createSqlServerCluster({ name: "sql-ag", domain_name: "corp.local", description: "primary", is_enabled: true }, client);
    await updateSqlServerCluster(1, { name: "sql-ag-updated", domain_name: "corp.local", description: null, is_enabled: false }, client);
    await syncSqlServerAvailabilityGroups(1, "master", client);
    await syncSqlServerClusterStatus(1, client);
    await syncSqlServerAgAccounts(1, client);
    await createMySqlCluster({ name: "mysql-repl", description: "replica", is_enabled: true }, client);
    await updateMySqlCluster(2, { name: "mysql-repl-updated", description: null, is_enabled: false }, client);
    await syncMySqlClusterTopology(2, client);
    await createInstance(
      {
        name: "mysql-new",
        db_type: "mysql",
        host: "10.0.0.10",
        port: 3306,
        database_name: "app_db",
        credential_id: 8,
        description: "new instance",
        tag_names: ["prod", "core"],
        is_active: true
      },
      client
    );
    await updateInstance(
      7,
      {
        name: "mysql-prod-updated",
        db_type: "mysql",
        host: "10.0.0.8",
        port: 3306,
        database_name: null,
        credential_id: null,
        description: null,
        tag_names: ["prod"],
        is_active: false
      },
      client
    );
    await testInstanceConnection(7, client);
    await batchTestInstanceConnections([7, 8], client);
    await deleteInstance(7, client);
    await restoreInstance(7, client);
    await refreshDatabaseTableSizes(9, client);
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
    await saveJumpServerSource({ credential_id: 3, base_url: "https://jump.example", org_id: "org-1", verify_ssl: true }, client);
    await unbindJumpServer(client);
    await syncVeeam(client);
    await createVeeamSource(
      {
        name: "veeam-main",
        credential_id: 4,
        server_host: "10.0.0.9",
        server_port: 9419,
        api_version: "v1",
        verify_ssl: false,
        match_domains: ["corp.local"]
      },
      client
    );
    await updateVeeamSource(
      9,
      {
        name: "veeam-main",
        credential_id: 4,
        server_host: "10.0.0.9",
        server_port: 9419,
        api_version: "v1",
        verify_ssl: true,
        match_domains: ["corp.local"]
      },
      client
    );
    await enableVeeamSource(9, client);
    await disableVeeamSource(9, client);
    await deleteVeeamSource(9, client);
    await syncAdDomains(client);
    await createAdDomainConfig(
      {
        name: "corp",
        netbios_name: "CORP",
        domain_controllers: ["dc01"],
        ldap_port: 636,
        use_ssl: true,
        verify_ssl: true,
        base_dn: "DC=corp,DC=local",
        credential_id: 5,
        is_enabled: true,
        description: "primary"
      },
      client
    );
    await updateAdDomainConfig(
      1,
      {
        name: "corp",
        netbios_name: "CORP",
        domain_controllers: ["dc01"],
        ldap_port: 636,
        use_ssl: true,
        verify_ssl: false,
        base_dn: "DC=corp,DC=local",
        credential_id: 5,
        is_enabled: false,
        description: null
      },
      client
    );
    await setAdDomainConfigEnabled(1, true, client);
    await testAdDomainConfig(1, client);
    await deleteAdDomainConfig(1, client);
    await createPartition(undefined, client);
    await cleanupPartitions(12, client);
    await createAccountClassification(
      { code: "ops", display_name: "运维", description: "ops accounts", risk_level: 3, icon_name: "shield", priority: 40 },
      client
    );
    await updateAccountClassification(
      5,
      { code: "ops", display_name: "运维账号", description: "ops accounts", risk_level: 2, icon_name: "shield", priority: 50 },
      client
    );
    await deleteAccountClassification(5, client);
    await createAccountClassificationRule(
      {
        rule_name: "root rule",
        classification_id: 5,
        db_type: "mysql",
        operator: "any",
        rule_expression: { fn: "username_like", args: ["root"] },
        is_active: true
      },
      client
    );
    await updateAccountClassificationRule(
      6,
      {
        rule_name: "readonly rule",
        classification_id: 5,
        db_type: "mysql",
        operator: "all",
        rule_expression: { fn: "privilege_contains", args: ["SELECT"] },
        is_active: false
      },
      client
    );
    await deleteAccountClassificationRule(6, client);
    await validateAccountClassificationRuleExpression({ fn: "username_like", args: ["root"] }, client);
    await updateSchedulerJob("job-1", { trigger_type: "cron", cron_expression: "*/10 * * * *" }, client);
    await createUser({ username: "ops_user", role: "user", password: "Aa123456", is_active: true }, client);
    await updateUser(7, { username: "ops_user", role: "admin", is_active: false }, client);
    await deleteUser(7, client);
    await createCredential(
      {
        name: "ops-db",
        credential_type: "database",
        db_type: "mysql",
        username: "app_user",
        password: "Strong123",
        description: "ops",
        is_active: true
      },
      client
    );
    await updateCredential(
      8,
      {
        name: "ops-db",
        credential_type: "database",
        db_type: "mysql",
        username: "app_user",
        is_active: false
      },
      client
    );
    await deleteCredential(8, client);
    await createTag({ name: "prod", display_name: "生产", category: "env", is_active: true }, client);
    await updateTag(9, { name: "prod", display_name: "生产环境", category: "env", is_active: false }, client);
    await deleteTag(9, client);
    await assignTagsToInstances([1, 2], [9], client);
    await removeTagsFromInstances([1], [9], client);
    await removeAllTagsFromInstances([2], client);

    expect(client.post).toHaveBeenCalledWith("/api/v1/capacity/aggregations/current", { scope: "database" });
    expect(client.post).toHaveBeenCalledWith("/api/v1/accounts/classifications/actions/auto-classify", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/databases/ledgers/actions/sync-all", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/instances/actions/sync-accounts", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/sqlserver-clusters", {
      name: "sql-ag",
      domain_name: "corp.local",
      description: "primary",
      is_enabled: true
    });
    expect(client.patch).toHaveBeenCalledWith("/api/v1/sqlserver-clusters/1", {
      name: "sql-ag-updated",
      domain_name: "corp.local",
      description: null,
      is_enabled: false
    });
    expect(client.post).toHaveBeenCalledWith("/api/v1/sqlserver-clusters/1/availability-groups/actions/sync", {
      connection_database: "master"
    });
    expect(client.post).toHaveBeenCalledWith("/api/v1/sqlserver-clusters/1/actions/sync-status", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/sqlserver-clusters/1/availability-groups/actions/sync-accounts", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/mysql-clusters", {
      name: "mysql-repl",
      description: "replica",
      is_enabled: true
    });
    expect(client.patch).toHaveBeenCalledWith("/api/v1/mysql-clusters/2", {
      name: "mysql-repl-updated",
      description: null,
      is_enabled: false
    });
    expect(client.post).toHaveBeenCalledWith("/api/v1/mysql-clusters/2/actions/sync-topology", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/instances", {
      name: "mysql-new",
      db_type: "mysql",
      host: "10.0.0.10",
      port: 3306,
      database_name: "app_db",
      credential_id: 8,
      description: "new instance",
      tag_names: ["prod", "core"],
      is_active: true
    });
    expect(client.put).toHaveBeenCalledWith("/api/v1/instances/7", {
      name: "mysql-prod-updated",
      db_type: "mysql",
      host: "10.0.0.8",
      port: 3306,
      database_name: null,
      credential_id: null,
      description: null,
      tag_names: ["prod"],
      is_active: false
    });
    expect(client.post).toHaveBeenCalledWith("/api/v1/instances/actions/test-connection", { instance_id: 7 });
    expect(client.post).toHaveBeenCalledWith("/api/v1/instances/actions/batch-test-connections", { instance_ids: [7, 8] });
    expect(client.delete).toHaveBeenCalledWith("/api/v1/instances/7");
    expect(client.post).toHaveBeenCalledWith("/api/v1/instances/7/actions/restore", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/databases/9/tables/sizes/actions/refresh?page=1&limit=20", {});
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
    expect(client.put).toHaveBeenCalledWith("/api/v1/integrations/jumpserver/source", {
      credential_id: 3,
      base_url: "https://jump.example",
      org_id: "org-1",
      verify_ssl: true
    });
    expect(client.delete).toHaveBeenCalledWith("/api/v1/integrations/jumpserver/source");
    expect(client.post).toHaveBeenCalledWith("/api/v1/integrations/veeam/actions/sync", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/integrations/veeam/sources", {
      name: "veeam-main",
      credential_id: 4,
      server_host: "10.0.0.9",
      server_port: 9419,
      api_version: "v1",
      verify_ssl: false,
      match_domains: ["corp.local"]
    });
    expect(client.put).toHaveBeenCalledWith("/api/v1/integrations/veeam/sources/9", {
      name: "veeam-main",
      credential_id: 4,
      server_host: "10.0.0.9",
      server_port: 9419,
      api_version: "v1",
      verify_ssl: true,
      match_domains: ["corp.local"]
    });
    expect(client.post).toHaveBeenCalledWith("/api/v1/integrations/veeam/sources/9/actions/enable", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/integrations/veeam/sources/9/actions/disable", {});
    expect(client.delete).toHaveBeenCalledWith("/api/v1/integrations/veeam/sources/9");
    expect(client.post).toHaveBeenCalledWith("/api/v1/ad-domain-configs/actions/sync", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/ad-domain-configs", {
      name: "corp",
      netbios_name: "CORP",
      domain_controllers: ["dc01"],
      ldap_port: 636,
      use_ssl: true,
      verify_ssl: true,
      base_dn: "DC=corp,DC=local",
      credential_id: 5,
      is_enabled: true,
      description: "primary"
    });
    expect(client.put).toHaveBeenCalledWith("/api/v1/ad-domain-configs/1", {
      name: "corp",
      netbios_name: "CORP",
      domain_controllers: ["dc01"],
      ldap_port: 636,
      use_ssl: true,
      verify_ssl: false,
      base_dn: "DC=corp,DC=local",
      credential_id: 5,
      is_enabled: false,
      description: null
    });
    expect(client.post).toHaveBeenCalledWith("/api/v1/ad-domain-configs/1/actions/set-enabled", { is_enabled: true });
    expect(client.post).toHaveBeenCalledWith("/api/v1/ad-domain-configs/1/actions/test-connection", {});
    expect(client.delete).toHaveBeenCalledWith("/api/v1/ad-domain-configs/1");
    expect(client.post).toHaveBeenCalledWith("/api/v1/partitions", {});
    expect(client.post).toHaveBeenCalledWith("/api/v1/partitions/actions/cleanup", { retention_months: 12 });
    expect(client.post).toHaveBeenCalledWith("/api/v1/accounts/classifications", {
      code: "ops",
      display_name: "运维",
      description: "ops accounts",
      risk_level: 3,
      icon_name: "shield",
      priority: 40
    });
    expect(client.put).toHaveBeenCalledWith("/api/v1/accounts/classifications/5", {
      code: "ops",
      display_name: "运维账号",
      description: "ops accounts",
      risk_level: 2,
      icon_name: "shield",
      priority: 50
    });
    expect(client.delete).toHaveBeenCalledWith("/api/v1/accounts/classifications/5");
    expect(client.post).toHaveBeenCalledWith("/api/v1/accounts/classifications/rules", {
      rule_name: "root rule",
      classification_id: 5,
      db_type: "mysql",
      operator: "any",
      rule_expression: { fn: "username_like", args: ["root"] },
      is_active: true
    });
    expect(client.put).toHaveBeenCalledWith("/api/v1/accounts/classifications/rules/6", {
      rule_name: "readonly rule",
      classification_id: 5,
      db_type: "mysql",
      operator: "all",
      rule_expression: { fn: "privilege_contains", args: ["SELECT"] },
      is_active: false
    });
    expect(client.delete).toHaveBeenCalledWith("/api/v1/accounts/classifications/rules/6");
    expect(client.post).toHaveBeenCalledWith("/api/v1/accounts/classifications/rules/actions/validate-expression", {
      rule_expression: { fn: "username_like", args: ["root"] }
    });
    expect(client.put).toHaveBeenCalledWith("/api/v1/scheduler/jobs/job-1", {
      trigger_type: "cron",
      cron_expression: "*/10 * * * *"
    });
    expect(client.post).toHaveBeenCalledWith("/api/v1/users", {
      username: "ops_user",
      role: "user",
      password: "Aa123456",
      is_active: true
    });
    expect(client.put).toHaveBeenCalledWith("/api/v1/users/7", {
      username: "ops_user",
      role: "admin",
      is_active: false
    });
    expect(client.delete).toHaveBeenCalledWith("/api/v1/users/7");
    expect(client.post).toHaveBeenCalledWith("/api/v1/credentials", {
      name: "ops-db",
      credential_type: "database",
      db_type: "mysql",
      username: "app_user",
      password: "Strong123",
      description: "ops",
      is_active: true
    });
    expect(client.put).toHaveBeenCalledWith("/api/v1/credentials/8", {
      name: "ops-db",
      credential_type: "database",
      db_type: "mysql",
      username: "app_user",
      is_active: false
    });
    expect(client.delete).toHaveBeenCalledWith("/api/v1/credentials/8");
    expect(client.post).toHaveBeenCalledWith("/api/v1/tags", {
      name: "prod",
      display_name: "生产",
      category: "env",
      is_active: true
    });
    expect(client.put).toHaveBeenCalledWith("/api/v1/tags/9", {
      name: "prod",
      display_name: "生产环境",
      category: "env",
      is_active: false
    });
    expect(client.delete).toHaveBeenCalledWith("/api/v1/tags/9");
    expect(client.post).toHaveBeenCalledWith("/api/v1/tags/bulk/actions/assign", { instance_ids: [1, 2], tag_ids: [9] });
    expect(client.post).toHaveBeenCalledWith("/api/v1/tags/bulk/actions/remove", { instance_ids: [1], tag_ids: [9] });
    expect(client.post).toHaveBeenCalledWith("/api/v1/tags/bulk/actions/remove-all", { instance_ids: [2] });
  });
});
