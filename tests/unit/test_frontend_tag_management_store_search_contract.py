"""Tag management store search contracts."""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]
TAG_MANAGEMENT_STORE_PATH = ROOT_DIR / "app/static/js/modules/stores/tag_management_store.js"


def test_tag_management_store_search_supports_code_display_name_and_category() -> None:
    if shutil.which("node") is None:
        pytest.skip("node 未安装，跳过基于真实 JS 运行时的标签搜索契约测试")

    script = textwrap.dedent(
        f"""
        const path = require("node:path");

        function createEmitter() {{
          const listeners = new Map();
          return {{
            all: listeners,
            on(eventName, handler) {{
              const queue = listeners.get(eventName) || [];
              queue.push(handler);
              listeners.set(eventName, queue);
            }},
            off(eventName, handler) {{
              const queue = listeners.get(eventName) || [];
              listeners.set(eventName, queue.filter((item) => item !== handler));
            }},
            emit(eventName, payload) {{
              const queue = listeners.get(eventName) || [];
              queue.forEach((handler) => handler(payload));
            }},
          }};
        }}

        global.window = {{
          LodashUtils: null,
          mitt() {{
            return createEmitter();
          }},
        }};

        require(path.resolve({json.dumps(str(TAG_MANAGEMENT_STORE_PATH))}));

        const service = {{
          listCategories() {{
            return Promise.resolve({{ categories: ["location", "architecture"] }});
          }},
          listTags() {{
            return Promise.resolve({{
              tags: [
                {{ id: 1, display_name: "上海", name: "shanghai", category: "location", is_active: true }},
                {{ id: 2, display_name: "主主", name: "master_master", category: "architecture", is_active: true }},
              ],
            }});
          }},
          batchDelete() {{
            return Promise.resolve({{ success: true }});
          }},
        }};

        async function main() {{
          const store = global.window.createTagManagementStore({{ service }});
          await store.init();

          store.actions.setSearch("shanghai");
          const codeMatches = store.getState().filteredTags.map((tag) => tag.id);

          store.actions.setSearch("上海");
          const displayNameMatches = store.getState().filteredTags.map((tag) => tag.id);

          store.actions.setSearch("location");
          const categoryMatches = store.getState().filteredTags.map((tag) => tag.id);

          process.stdout.write(JSON.stringify({{
            codeMatches,
            displayNameMatches,
            categoryMatches,
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

    assert payload["codeMatches"] == [1]
    assert payload["displayNameMatches"] == [1]
    assert payload["categoryMatches"] == [1]
