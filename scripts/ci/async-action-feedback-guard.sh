#!/usr/bin/env bash
# Async action feedback guard (warn-first): 查找缺少 unknown fallback 的 if/else if(success/error) 模式

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${TARGET_DIR:-app/static/js/modules/views}"
MODE="${1:-warn}"

STRICT="false"
if [[ "${MODE}" == "strict" ]]; then
  STRICT="true"
fi

cd "${ROOT_DIR}"

export STRICT
python3 - <<'PY'
from __future__ import annotations

import os
import pathlib
import re
import sys


root_dir = pathlib.Path(os.environ.get("ROOT_DIR", ".")).resolve()
target_dir = root_dir / os.environ.get("TARGET_DIR", "app/static/js/modules/views")
strict = os.environ.get("STRICT", "false").lower() in {"1", "true", "yes", "on"}

success_token = r"(?:\?\.\s*|\.\s*)success\b"
error_token = r"(?:\?\.\s*|\.\s*)error\b"

pattern = re.compile(
    rf"if\s*\([^)]*{success_token}[^)]*\)\s*\{{[^{{}}]*\}}\s*else\s+if\s*\([^)]*{error_token}[^)]*\)\s*\{{[^{{}}]*\}}\s*(?!\s*else)",
)

hits: list[str] = []
if not target_dir.exists():
    print(f"未找到目标目录：{target_dir}，跳过检查。")
    raise SystemExit(0)

for path in sorted(target_dir.rglob("*.js")):
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue

    for match in pattern.finditer(content):
        line_no = content.count("\n", 0, match.start()) + 1
        relative_path = path.relative_to(root_dir)
        hits.append(f"{relative_path}:{line_no}")

if not hits:
    print("✅ async-action-feedback 门禁通过：未发现疑似缺少 unknown fallback 的 success/error 分支。")
    raise SystemExit(0)

print("⚠️ 检测到疑似缺少 unknown fallback 的 async action 分支（warn-first，不阻断）:")
print("\n".join(hits))
print("")
print("建议：统一使用 UI.resolveAsyncActionOutcome(...) 并补齐 unknown 分支提示，避免静默。")
print("参考：docs/standards/ui/async-task-feedback-guidelines.md")

raise SystemExit(1 if strict else 0)
PY
