import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { LineChart } from "recharts";
import { describe, expect, it } from "vitest";

import { ChartContainer } from "./chart";

describe("ChartContainer", () => {
  it("defines every shared chart palette token with visible colors", () => {
    const css = readFileSync(resolve(__dirname, "../../styles.css"), "utf8");

    for (const token of ["--chart-1", "--chart-2", "--chart-3", "--chart-4", "--chart-5"]) {
      const match = css.match(new RegExp(`${token}:\\s*([^;]+);`));

      expect(match?.[1]?.trim()).toMatch(/^#[0-9a-f]{6}$/i);
      expect(match?.[1]?.trim().toLowerCase()).not.toBe("#ffffff");
    }
  });

  it("uses non-white shared chart chrome for grids and tooltip cursors", () => {
    render(
      <ChartContainer aria-label="趋势图" config={{ total: { color: "#b85c1e" } }}>
        <LineChart data={[]} />
      </ChartContainer>
    );

    const chart = screen.getByLabelText("趋势图");

    expect(chart).toHaveClass("[&_.recharts-cartesian-grid_line]:stroke-foreground/15");
    expect(chart).toHaveClass("[&_.recharts-tooltip-cursor]:stroke-foreground/35");
    expect(chart).toHaveClass("[&_.recharts-rectangle.recharts-tooltip-cursor]:fill-foreground/10");
  });
});
