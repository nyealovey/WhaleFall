import * as React from "react";
import {
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  type ResponsiveContainerProps,
  type TooltipContentProps
} from "recharts";

import { cn } from "@/utils/cn";

export type ChartConfig = Record<
  string,
  {
    label?: React.ReactNode;
    color?: string;
  }
>;

type ChartContainerProps = React.ComponentProps<"div"> & {
  config: ChartConfig;
  children: ResponsiveContainerProps["children"];
};

function ChartContainer({ id, className, children, config, style, ...props }: ChartContainerProps) {
  const uniqueId = React.useId();
  const chartId = `chart-${id ?? uniqueId.replace(/:/g, "")}`;
  const chartStyle = Object.fromEntries(
    Object.entries(config).map(([key, value]) => [`--color-${key}`, value.color])
  ) as React.CSSProperties;

  return (
    <div
      data-chart={chartId}
      data-slot="chart"
      className={cn(
        "flex aspect-video justify-center text-xs text-muted-foreground",
        "[&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground [&_.recharts-cartesian-axis-line]:stroke-foreground/20 [&_.recharts-cartesian-axis-tick-line]:stroke-foreground/20",
        "[&_.recharts-cartesian-grid_line]:stroke-foreground/15 [&_.recharts-reference-line_line]:stroke-foreground/20",
        "[&_.recharts-tooltip-cursor]:stroke-foreground/35 [&_.recharts-curve.recharts-tooltip-cursor]:stroke-foreground/35",
        "[&_.recharts-rectangle.recharts-tooltip-cursor]:fill-foreground/10 [&_.recharts-rectangle.recharts-tooltip-cursor]:stroke-foreground/20",
        "[&_.recharts-dot[stroke='#fff']]:stroke-transparent",
        "[&_.recharts-layer]:outline-hidden [&_.recharts-sector]:outline-hidden [&_.recharts-surface]:outline-hidden",
        className
      )}
      style={{ ...chartStyle, ...style }}
      {...props}
    >
      <ResponsiveContainer initialDimension={{ width: 400, height: 200 }} minHeight={0} minWidth={0}>
        {children}
      </ResponsiveContainer>
    </div>
  );
}

const ChartTooltip = RechartsTooltip;

function ChartTooltipContent({
  active,
  payload,
  label,
  className,
  hideLabel = false
}: Partial<TooltipContentProps<number, string>> & {
  className?: string;
  hideLabel?: boolean;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className={cn("grid min-w-28 gap-1.5 rounded-md border bg-popover px-2.5 py-2 text-xs shadow-md", className)}>
      {hideLabel ? null : <div className="font-medium text-popover-foreground">{label}</div>}
      <div className="grid gap-1.5">
        {payload.map((item) => (
          <div className="flex items-center justify-between gap-3" key={`${item.dataKey ?? item.name}`}>
            <div className="flex items-center gap-1.5">
              <span
                className="size-2 rounded-[2px]"
                style={{ backgroundColor: item.color ?? item.payload?.fill ?? "var(--primary)" }}
              />
              <span className="text-muted-foreground">{String(item.name ?? item.dataKey)}</span>
            </div>
            <span className="font-mono font-medium text-popover-foreground">{String(item.value ?? "-")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export { ChartContainer, ChartTooltip, ChartTooltipContent };
