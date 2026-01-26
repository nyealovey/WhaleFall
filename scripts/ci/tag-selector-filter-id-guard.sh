#!/usr/bin/env bash
# TagSelectorFilter DOM id 门禁：禁止回归固定全局 id（同页多实例会冲突）
#
# 参考：
# - docs/Obsidian/standards/ui/gate/component-dom-id-scope.md

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGETS=(
  "${ROOT_DIR}/app/templates"
  "${ROOT_DIR}/app/static/js"
)

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，无法执行 TagSelectorFilter id 门禁检查。" >&2
  exit 1
fi

FIXED_ID_PATTERN='open-tag-filter-btn|selected-tag-names|selected-tags-preview|selected-tags-chips'

if "${RG_BIN}" -n "${FIXED_ID_PATTERN}" "${TARGETS[@]}"; then
  echo "" >&2
  echo "检测到 TagSelectorFilter 使用固定全局 DOM id（同页多实例会冲突）。" >&2
  echo "请改为：data-tag-selector-scope + <scope>-* 派生 id，并在 JS 中以容器作用域查询。" >&2
  echo "参考：docs/Obsidian/standards/ui/gate/component-dom-id-scope.md" >&2
  exit 1
fi

echo "✅ TagSelectorFilter id 门禁通过：未发现固定全局 DOM id。"
