"""Capacity chart legend interaction contracts."""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]
CHART_RENDERER_PATH = ROOT_DIR / "app/static/js/modules/views/components/charts/chart-renderer.js"


def test_capacity_chart_external_legend_supports_click_toggle() -> None:
    if shutil.which("node") is None:
        pytest.skip("node 未安装，跳过基于真实 JS 运行时的容量图例交互测试")

    script = textwrap.dedent(
        f"""
        const path = require("node:path");

        class FakeElement {{
          constructor(tagName = "div") {{
            this.tagName = String(tagName || "div").toUpperCase();
            this.children = [];
            this.hidden = false;
            this.dataset = {{}};
            this.textContent = "";
            this.className = "";
            this.listeners = {{}};
            this.style = {{
              values: {{}},
              setProperty: (name, value) => {{
                this.style.values[name] = value;
              }},
            }};
            this.attributes = {{}};
          }}

          appendChild(child) {{
            if (!child) {{
              return child;
            }}
            if (child.isFragment) {{
              child.children.forEach((item) => this.appendChild(item));
              return child;
            }}
            this.children.push(child);
            return child;
          }}

          replaceChildren(...items) {{
            this.children = [];
            items.forEach((item) => this.appendChild(item));
          }}

          addEventListener(eventName, handler) {{
            this.listeners[eventName] = handler;
          }}

          setAttribute(name, value) {{
            this.attributes[name] = String(value);
          }}

          getAttribute(name) {{
            return this.attributes[name];
          }}
        }}

        class FakeFragment {{
          constructor() {{
            this.isFragment = true;
            this.children = [];
          }}

          appendChild(child) {{
            this.children.push(child);
            return child;
          }}
        }}

        const legend = new FakeElement("aside");
        const canvas = new FakeElement("canvas");
        canvas.getContext = () => ({{}});

        const registry = {{
          "#chart": canvas,
          "#legend": legend,
        }};

        global.Element = FakeElement;
        global.document = {{
          documentElement: {{}},
          createElement(tagName) {{
            return new FakeElement(tagName);
          }},
          createDocumentFragment() {{
            return new FakeFragment();
          }},
        }};
        global.getComputedStyle = () => ({{ color: "#222222" }});

        const selectOne = (selector) => ({{
          first() {{
            return registry[selector] || null;
          }},
        }});

        const chartInstances = [];
        class FakeChart {{
          constructor(_ctx, config) {{
            this.data = config.data;
            this.visibility = (config.data?.datasets || []).map(() => true);
            this.updateCalls = 0;
            this.setVisibilityCalls = [];
            chartInstances.push(this);
          }}

          destroy() {{}}

          isDatasetVisible(index) {{
            return this.visibility[index] !== false;
          }}

          setDatasetVisibility(index, visible) {{
            this.visibility[index] = Boolean(visible);
            this.setVisibilityCalls.push([index, Boolean(visible)]);
          }}

          update() {{
            this.updateCalls += 1;
          }}
        }}

        global.window = {{
          DOMHelpers: {{ selectOne }},
          ColorTokens: {{
            resolveCssVar() {{ return "#111111"; }},
            getOrangeColor() {{ return "rgba(255, 128, 0, 0.2)"; }},
            getChartColor() {{ return "rgba(0, 128, 255, 0.2)"; }},
            getSurfaceColor() {{ return "rgba(0, 0, 0, 0.08)"; }},
            withAlpha(color, alpha) {{ return `${{color}}-${{alpha}}`; }},
          }},
          NumberFormat: {{
            formatPlain(value) {{ return String(value); }},
            formatPercent(value) {{ return String(value); }},
          }},
          Chart: FakeChart,
          document: global.document,
        }};

        require(path.resolve({json.dumps(str(CHART_RENDERER_PATH))}));

        global.window.CapacityStatsChartRenderer.renderTrendChart({{
          canvas: "#chart",
          legendContainer: "#legend",
          instance: null,
          type: "line",
          data: {{
            labels: ["2026-03-11", "2026-03-12"],
            datasets: [
              {{ label: "gf-mssqlag-01", data: [1, 2], borderColor: "#1f77b4" }},
              {{ label: "gf-mssqlag-02", data: [2, 3], borderColor: "#ff7f0e" }},
            ],
          }},
        }});

        const firstItem = legend.children[0];
        const beforeClickHasListener = Boolean(firstItem?.listeners?.click);
        if (firstItem?.listeners?.click) {{
          firstItem.listeners.click({{ preventDefault() {{}} }});
        }}

        process.stdout.write(JSON.stringify({{
          legendHidden: legend.hidden,
          legendCount: legend.children.length,
          beforeClickHasListener,
          firstTag: firstItem?.tagName || null,
          firstAriaPressed: firstItem?.getAttribute?.("aria-pressed") || null,
          firstClassName: firstItem?.className || "",
          chartUpdateCalls: chartInstances[0]?.updateCalls || 0,
          setVisibilityCalls: chartInstances[0]?.setVisibilityCalls || [],
          firstItemClassAfterClick: legend.children[0]?.className || "",
        }}));
        """
    )

    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT_DIR,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)

    assert payload["legendHidden"] is False
    assert payload["legendCount"] == 2
    assert payload["beforeClickHasListener"] is True
    assert payload["firstTag"] == "BUTTON"
    assert payload["chartUpdateCalls"] == 1
    assert payload["setVisibilityCalls"] == [[0, False]]
    assert "capacity-chart-legend__item--muted" in payload["firstItemClassAfterClick"]
