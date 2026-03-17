"""Tag selector item rendering contracts."""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]
TAG_SELECTOR_VIEW_PATH = ROOT_DIR / "app/static/js/modules/views/components/tags/tag-selector-view.js"


def test_tag_selector_compacts_available_and_selected_items() -> None:
    if shutil.which("node") is None:
        pytest.skip("node 未安装，跳过基于真实 JS 运行时的标签卡片渲染测试")

    script = textwrap.dedent(
        f"""
        const path = require("node:path");

        class FakeElement {{
          constructor(name = "div", map = {{}}) {{
            this.name = name;
            this.map = map;
            this.innerHTML = "";
            this.dataset = {{}};
            this.hidden = false;
            this.listeners = {{}};
            this.classList = {{
              toggle() {{}},
              add() {{}},
              remove() {{}},
              contains() {{ return false; }},
            }};
          }}

          querySelector(selector) {{
            return this.map[selector] || null;
          }}

          querySelectorAll() {{
            return [];
          }}

          addEventListener(eventName, handler) {{
            this.listeners[eventName] = handler;
          }}

          setAttribute(name, value) {{
            this[name] = value;
          }}
        }}

        const tagList = new FakeElement("tagList");
        const selectedList = new FakeElement("selectedList");
        const selectedEmpty = new FakeElement("selectedEmpty");
        const root = new FakeElement("root", {{
          '[data-role="tag-list"]': tagList,
          '[data-role="selected-list"]': selectedList,
          '[data-role="selected-empty"]': selectedEmpty,
        }});

        global.Element = FakeElement;
        global.document = {{ querySelector() {{ return null; }} }};
        global.window = {{
          document: global.document,
          LodashUtils: null,
          NumberFormat: null,
          console,
        }};

        require(path.resolve({json.dumps(str(TAG_SELECTOR_VIEW_PATH))}));

        const view = new global.window.TagSelectorView(root, {{
          onCategoryChange() {{}},
          onTagToggle() {{}},
          onSelectedRemove() {{}},
        }});

        const tag = {{
          id: 1,
          display_name: "上海",
          name: "SHANGHAI",
          category: "LOCATION",
          is_active: true,
        }};

        view.renderTagList([tag], new Set([1]));
        view.updateSelectedDisplay([tag]);

        process.stdout.write(JSON.stringify({{
          availableHtml: tagList.innerHTML,
          selectedHtml: selectedList.innerHTML,
          selectedEmptyHidden: selectedEmpty.hidden,
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
    available_html = payload["availableHtml"]
    selected_html = payload["selectedHtml"]

    assert "tag-selector__item-summary" in available_html
    assert "tag-selector__selected-item-summary" in selected_html
    assert "上海" in available_html
    assert "上海" in selected_html
    assert "LOCATION" in available_html
    assert "LOCATION" in selected_html
    assert "SHANGHAI" not in available_html
    assert "SHANGHAI" not in selected_html
    assert "tag-selector__item-subtitle" not in available_html
    assert payload["selectedEmptyHidden"] is True
