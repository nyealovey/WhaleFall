import { describe, expect, it } from "vitest";

import { formatCapacityMb, formatDateTime, formatDatabaseType, formatStatus } from "./display";

describe("display formatters", () => {
  it("formats capacity with adaptive MB, GB, and TB units", () => {
    expect(formatCapacityMb(512)).toBe("512 MB");
    expect(formatCapacityMb(1536)).toBe("1.50 GB");
    expect(formatCapacityMb(1572864)).toBe("1.50 TB");
  });

  it("formats database types, statuses, and local time as business text", () => {
    expect(formatDatabaseType("sqlserver")).toBe("SQL Server");
    expect(formatStatus("completed_with_errors")).toBe("部分完成");
    expect(formatDateTime(null)).toBe("-");
  });
});
