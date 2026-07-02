import { describe, expect, it } from "vitest";

import { buildAuditSpecRows, buildAuditTargetRows } from "./instanceAuditView";

describe("instance audit view mapping", () => {
  it("maps audit target fields from the SQL Server snapshot", () => {
    const rows = buildAuditTargetRows([
      {
        name: "SIEM",
        enabled: true,
        target_type: "APPLICATION LOG",
        target_summary: "APPLICATION LOG",
        queue_delay: 1000,
        on_failure: "CONTINUE",
        updated_at: "2023-08-04T16:11:52+00:00"
      }
    ]);

    expect(rows[0]).toMatchObject({
      name: "SIEM",
      status: "启用",
      targetType: "APPLICATION LOG",
      targetSummary: ["APPLICATION LOG", "Queue delay: 1000 ms"],
      failurePolicy: "CONTINUE",
      updatedAt: "2023-08-04 16:11:52"
    });
  });

  it("maps audit specification scope, bound audit and action preview", () => {
    const rows = buildAuditSpecRows([
      {
        scope: "server",
        name: "Audit_Server_Configuration_Changes",
        audit_name: "SIEM",
        enabled: true,
        action_count: 2,
        actions: [{ display_text: "APPLICATION_ROLE_CHANGE_PASSWORD_GROUP" }, { display_text: "AUDIT_CHANGE_GROUP" }]
      },
      {
        scope: "database",
        database_name: "master",
        name: "Audit_OSCMDEXEC",
        audit_name: "SIEM",
        enabled: true,
        actions: [{ display_text: "EXECUTE sys.xp_cmdshell" }]
      }
    ]);

    expect(rows[0]).toMatchObject({
      scopeLabel: "SERVER",
      scopeDetail: "实例级",
      boundAudit: "SIEM",
      status: "启用",
      actionCount: 2,
      actionPreview: ["APPLICATION_ROLE_CHANGE_PASSWORD_GROUP", "AUDIT_CHANGE_GROUP"]
    });
    expect(rows[1]).toMatchObject({
      scopeLabel: "DATABASE",
      scopeDetail: "master",
      actionCount: 1,
      actionPreview: ["EXECUTE sys.xp_cmdshell"]
    });
  });
});
