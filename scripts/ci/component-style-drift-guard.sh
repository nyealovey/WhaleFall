#!/usr/bin/env bash
# 共享组件样式漂移门禁：防止 pages 层重复定义 status-pill / button roles 等共享组件类，导致跨页面样式漂移
#
# 参考：
# - docs/Obsidian/standards/ui/gate/button-hierarchy.md
# - docs/Obsidian/standards/ui/guide/color.md

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${ROOT_DIR}/app/static/css/pages"

PY_BIN="${PY_BIN:-python3}"
if ! command -v "${PY_BIN}" >/dev/null 2>&1; then
  echo "未检测到 python3，无法执行共享组件样式漂移门禁检查。" >&2
  exit 1
fi

if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "未找到 ${TARGET_DIR}，跳过检查。"
  exit 0
fi

# 说明：
# - 禁止在 pages 层用裸共享组件选择器开头定义样式，例如 `.card {}` / `.card-body > ...` / `.btn-primary:hover {}`。
# - 页面确需差异时，必须先加页面/局部作用域，例如 `.accounts-grid-stage .card-body`。
"${PY_BIN}" - <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

target_dir = Path("app/static/css/pages")
shared_roots = (
    "status-pill",
    "btn",
    "btn-icon",
    "btn-command",
    "btn-table-action",
    "btn-segment",
    "btn-form-action",
    "btn-quick-action",
    "command-action-bar",
    "table-action-bar",
    "segmented-control",
    "form-action-row",
    "card",
    "card-body",
    "card-header",
    "card-title",
    "modal",
    "modal-dialog",
    "modal-body",
    "modal-footer",
    "wf-modal",
    "wf-metric-card",
    "filter-card",
    "table",
    "gridjs",
    "badge",
    "chip-outline",
    "form-control",
    "input-group",
    "nav-link",
)

root_pattern = re.compile(
    r"^\.(?:"
    + "|".join(re.escape(root) for root in sorted(shared_roots, key=len, reverse=True))
    + r")(?:$|[\s.#:[>+~])"
)


def strip_comments(content: str) -> str:
    return re.sub(r"/\*.*?\*/", "", content, flags=re.S)


def iter_selectors(content: str):
    cleaned = strip_comments(content)
    for match in re.finditer(r"(?P<selectors>[^{}]+)\{", cleaned, re.S):
        selectors = " ".join(match.group("selectors").split())
        if not selectors or selectors.startswith("@"):
            continue
        yield cleaned.count("\n", 0, match.start()) + 1, selectors


offenders: list[str] = []
for path in sorted(target_dir.rglob("*.css")):
    content = path.read_text(encoding="utf-8", errors="ignore")
    for line, selector_group in iter_selectors(content):
        for selector in selector_group.split(","):
            selector = selector.strip()
            if root_pattern.search(selector):
                offenders.append(f"{path}:{line}: {selector}")

if offenders:
    print("", file=sys.stderr)
    print("检测到 pages 层裸共享组件选择器，可能导致多套 CSS 互相覆盖：", file=sys.stderr)
    print("", file=sys.stderr)
    print("\n".join(offenders[:120]), file=sys.stderr)
    print("", file=sys.stderr)
    print("修复建议：", file=sys.stderr)
    print("- 组件基线集中到 app/static/css/components/ 或 app/static/css/global.css。", file=sys.stderr)
    print("- 页面差异必须先加局部作用域，例如 .page-root .card / .accounts-grid-stage .card-body。", file=sys.stderr)
    print("- 如果是新页面专属元素，使用页面语义类，不要直接复写 Bootstrap/共享组件类。", file=sys.stderr)
    print("参考：", file=sys.stderr)
    print("- docs/Obsidian/standards/ui/gate/button-hierarchy.md", file=sys.stderr)
    print("- docs/Obsidian/standards/ui/guide/color.md", file=sys.stderr)
    sys.exit(1)

print("✅ 共享组件样式漂移门禁通过：未发现 pages 层裸共享组件选择器。")
PY
