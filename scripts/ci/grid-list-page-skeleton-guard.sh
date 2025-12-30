#!/usr/bin/env bash
# Grid list page skeleton guard (warn-first): 检测 views 层重复 helper / 直接 new GridWrapper

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${TARGET_DIR:-app/static/js/modules/views}"
MODE="${1:-warn}"

STRICT="false"
if [[ "${MODE}" == "strict" ]]; then
  STRICT="true"
fi

cd "${ROOT_DIR}"

export ROOT_DIR
export TARGET_DIR
export STRICT

python3 - <<'PY'
from __future__ import annotations

import os
import pathlib
import re


root_dir = pathlib.Path(os.environ.get("ROOT_DIR", ".")).resolve()
target_dir = root_dir / os.environ.get("TARGET_DIR", "app/static/js/modules/views")
strict = os.environ.get("STRICT", "false").lower() in {"1", "true", "yes", "on"}

if not target_dir.exists():
    print(f"未找到目标目录：{target_dir}，跳过检查。")
    raise SystemExit(0)


patterns: dict[str, re.Pattern[str]] = {
    "function escapeHtml(": re.compile(r"\bfunction\s+escapeHtml\s*\("),
    "function resolveErrorMessage(": re.compile(r"\bfunction\s+resolveErrorMessage\s*\("),
    "function renderChipStack(": re.compile(r"\bfunction\s+renderChipStack\s*\("),
}

grid_wrapper_pattern = re.compile(r"\bnew\s+GridWrapper\s*\(")

allowed_grid_wrapper_files = {
    root_dir / "app/static/js/modules/views/grid-page.js",
}

hits: dict[str, list[str]] = {name: [] for name in patterns}
grid_wrapper_hits: list[str] = []

for path in sorted(target_dir.rglob("*.js")):
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue

    relative_path = path.relative_to(root_dir)

    for name, pattern in patterns.items():
        for match in pattern.finditer(content):
            line_no = content.count("\n", 0, match.start()) + 1
            hits[name].append(f"{relative_path}:{line_no}")

    if path not in allowed_grid_wrapper_files:
        for match in grid_wrapper_pattern.finditer(content):
            line_no = content.count("\n", 0, match.start()) + 1
            grid_wrapper_hits.append(f"{relative_path}:{line_no}")


has_hits = grid_wrapper_hits or any(items for items in hits.values())
if not has_hits:
    print("✅ grid list page skeleton 门禁通过：未发现重复 helper / 直接 new GridWrapper。")
    raise SystemExit(0)

print("⚠️ 检测到疑似违反 grid list page skeleton 单一真源的实现（warn-first，不阻断）:")

if grid_wrapper_hits:
    print("")
    print("【禁止：views 内直接 new GridWrapper】")
    print("\n".join(grid_wrapper_hits))

for name, items in hits.items():
    if not items:
        continue
    print("")
    print(f"【禁止：views 内新增 {name}】")
    print("\n".join(items))

print("")
print("建议：")
print("- helpers 统一使用：UI.escapeHtml / UI.resolveErrorMessage / UI.renderChipStack")
print("- row meta 统一使用：GridRowMeta.get(row)")
print("- list wiring 统一使用：Views.GridPage + plugins")
print("")
print("参考：docs/standards/ui/grid-list-page-skeleton-guidelines.md")

raise SystemExit(1 if strict else 0)
PY
