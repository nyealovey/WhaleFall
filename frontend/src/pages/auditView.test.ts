import { describe, expect, it } from "vitest";

import { historyLogLevelLabel, historyLogMessageLabel, historyLogModuleLabel } from "./auditView";

describe("audit view helpers", () => {
  it("uses backend localized labels for history logs", () => {
    const log = {
      level: "INFO",
      level_label: "信息",
      module: "http",
      module_label: "HTTP 请求",
      message: "http_request_completed",
      message_label: "HTTP 请求完成"
    };

    expect(historyLogLevelLabel(log)).toBe("信息");
    expect(historyLogModuleLabel(log)).toBe("HTTP 请求");
    expect(historyLogMessageLabel(log)).toBe("HTTP 请求完成");
  });

  it("falls back to raw fields when legacy responses miss labels", () => {
    const log = {
      level: "INFO",
      level_label: "",
      module: "http",
      module_label: "",
      message: "http_request_completed",
      message_label: ""
    };

    expect(historyLogLevelLabel(log)).toBe("INFO");
    expect(historyLogModuleLabel(log)).toBe("http");
    expect(historyLogMessageLabel(log)).toBe("http_request_completed");
  });
});
