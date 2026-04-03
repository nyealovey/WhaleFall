"""Tag selector category rendering contracts."""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]


def test_tag_selector_renders_string_categories_as_full_labels() -> None:
    if shutil.which("node") is None:
        pytest.skip("node 未安装，跳过基于真实 JS 运行时的标签分类渲染测试")

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

        const categoryGroup = new FakeElement("categoryGroup");
        const categoryLoading = new FakeElement("categoryLoading");
        categoryLoading.remove = function remove() {{}};
        const tagList = new FakeElement("tagList");
        const selectedList = new FakeElement("selectedList");
        const selectedEmpty = new FakeElement("selectedEmpty");

        const root = new FakeElement("root", {{
          '[data-role="category-group"]': categoryGroup,
          '[data-role="category-loading"]': categoryLoading,
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

        require(path.resolve({json.dumps(str(ROOT_DIR / "app/static/js/modules/views/components/tags/tag-selector-view.js"))}));

        const view = new global.window.TagSelectorView(root, {{
          onCategoryChange() {{}},
          onTagToggle() {{}},
          onSelectedRemove() {{}},
        }});

        view.renderCategories(["environment", "location"]);

        process.stdout.write(JSON.stringify({{ html: categoryGroup.innerHTML }}));
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
    html = payload["html"]

    assert 'data-category-value="environment"' in html
    assert 'data-category-value="location"' in html
    assert ">environment" in html
    assert ">location" in html
