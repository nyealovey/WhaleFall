import { render, screen } from "@testing-library/react";
import { LineChart } from "recharts";
import { describe, expect, it } from "vitest";

import { ChartContainer } from "./chart";

describe("ChartContainer", () => {
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
