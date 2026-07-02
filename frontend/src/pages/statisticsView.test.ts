import { describe, expect, it } from "vitest";

import { formatStatisticsSizeMb } from "./statisticsView";

describe("statistics view helpers", () => {
  it("formats capacity values with MB, GB and TB units", () => {
    expect(formatStatisticsSizeMb(512)).toBe("512.00 MB");
    expect(formatStatisticsSizeMb(2048)).toBe("2.00 GB");
    expect(formatStatisticsSizeMb(2 * 1024 * 1024)).toBe("2.00 TB");
  });
});
