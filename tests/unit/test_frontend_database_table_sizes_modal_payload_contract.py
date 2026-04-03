"""Database table sizes modal payload contract tests."""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
MODAL_VIEW_PATH = ROOT_DIR / "app/static/js/modules/views/instances/modals/database-table-sizes-modal.js"


def test_database_table_sizes_modal_parses_json_payload_from_ui_modal() -> None:
    if shutil.which("node") is None:
        pytest.skip("node 未安装，跳过基于真实 JS 运行时的表容量模态测试")

    script = textwrap.dedent(
        f"""
        const path = require("node:path");

        class FakeElement {{
          constructor(id) {{
            this.id = id;
            this.innerHTML = "";
            this.textContent = "";
            this.dataset = {{}};
            this.listeners = {{}};
          }}

          addEventListener(eventName, handler) {{
            this.listeners[eventName] = handler;
          }}

          querySelector() {{
            return null;
          }}
        }}

        const modalEl = new FakeElement("tableSizesModal");
        const dbNameEl = new FakeElement("tableSizesModalDatabaseName");
        const collectedAtEl = new FakeElement("tableSizesModalCollectedAt");
        const gridContainer = new FakeElement("tableSizesGrid");

        const elements = {{
          tableSizesModal: modalEl,
          tableSizesModalDatabaseName: dbNameEl,
          tableSizesModalCollectedAt: collectedAtEl,
          tableSizesGrid: gridContainer,
        }};

        let capturedDatabaseId = null;
        let capturedParams = null;
        const toastErrors = [];

        global.document = {{
          getElementById(id) {{
            return elements[id] || null;
          }},
        }};

        global.window = {{
          UI: {{
            createModal(options) {{
              return {{
                open(payload) {{
                  options.onOpen?.({{
                    modal: {{ setLoading() {{}} }},
                    payload: payload ? JSON.stringify(payload) : "",
                  }});
                }},
                close() {{}},
                setLoading() {{}},
              }};
            }},
            escapeHtml(value) {{
              return String(value ?? "");
            }},
            resolveErrorMessage(error, fallback) {{
              return error?.message || fallback;
            }},
          }},
          GridTable: {{
            create() {{
              return {{
                render(target) {{
                  target.innerHTML = "<table></table>";
                }},
                destroy() {{}},
              }};
            }},
          }},
          toast: {{
            success() {{}},
            error(message) {{
              toastErrors.push(message);
            }},
          }},
        }};

        const store = {{
          actions: {{
            fetchDatabaseTableSizes(databaseId, params) {{
              capturedDatabaseId = databaseId;
              capturedParams = params;
              return Promise.resolve({{ data: {{ collected_at: "2026-03-17T10:00:00", tables: [] }} }});
            }},
            refreshDatabaseTableSizes() {{
              return Promise.resolve({{ data: {{ tables: [] }} }});
            }},
          }},
        }};

        require(path.resolve({json.dumps(str(MODAL_VIEW_PATH))}));

        async function main() {{
          const controller = global.window.InstanceDatabaseTableSizesModal.createController({{
            ui: global.window.UI,
            toast: global.window.toast,
            store,
          }});

          controller.open(123, "app_db");
          await new Promise((resolve) => setTimeout(resolve, 0));

          process.stdout.write(JSON.stringify({{
            capturedDatabaseId,
            capturedParams,
            databaseName: dbNameEl.textContent,
            toastErrors,
          }}));
        }}

        main().catch((error) => {{
          console.error(error);
          process.exit(1);
        }});
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

    assert payload["capturedDatabaseId"] == 123
    assert payload["capturedParams"] == {"limit": 2000, "page": 1}
    assert payload["databaseName"] == "app_db"
    assert payload["toastErrors"] == []
