#!/usr/bin/env bash
# 共享组件样式漂移门禁：防止 pages 层重复定义 status-pill / btn-icon 等共享组件类，导致跨页面样式漂移
#
# 参考：
# - docs/Obsidian/standards/ui/gate/button-hierarchy.md
# - docs/Obsidian/standards/ui/guide/color.md

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${ROOT_DIR}/app/static/css/pages"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，无法执行共享组件样式漂移门禁检查。" >&2
  exit 1
fi

if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "未找到 ${TARGET_DIR}，跳过检查。"
  exit 0
fi

# 说明：
# - 禁止在 pages 层重复定义共享组件类（例如 `.status-pill {}` / `.btn-icon {}`）。
# - 如需页面特殊布局，仅允许在容器作用域内覆写（例如 `.job-actions .btn-icon {}`），避免污染整个页面。
PATTERN='^\s*\.(status-pill|btn-icon)\b'

matches="$("${RG_BIN}" -n --glob "*.css" "${PATTERN}" "${TARGET_DIR}" || true)"
if [[ -n "${matches}" ]]; then
  echo "" >&2
  echo "检测到 pages 层重复定义共享组件类（status-pill / btn-icon），可能导致跨页面样式漂移：" >&2
  echo "" >&2
  printf "%s\n" "${matches}" >&2
  echo "" >&2
  echo "修复建议：" >&2
  echo "- 组件基线请集中到 components：" >&2
  echo "  - status-pill：app/static/css/components/status-pill.css" >&2
  echo "  - btn-icon：app/static/css/components/buttons.css" >&2
  echo "- 页面确需差异时，请改为容器作用域覆写（例如 .page-scope .status-pill / .page-scope .btn-icon）。" >&2
  echo "参考：" >&2
  echo "- docs/Obsidian/standards/ui/gate/button-hierarchy.md" >&2
  echo "- docs/Obsidian/standards/ui/guide/color.md" >&2
  exit 1
fi

echo "✅ 共享组件样式漂移门禁通过：未发现 pages 层重复定义 status-pill / btn-icon。"
