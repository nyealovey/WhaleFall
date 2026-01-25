#!/usr/bin/env bash
# 分页参数门禁：GridWrapper 必须使用 limit 作为分页大小参数
#
# 参考：
# - docs/Obsidian/standards/ui/gate/grid.md

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GRID_WRAPPER_FILE="${ROOT_DIR}/app/static/js/common/grid-wrapper.js"
TABLE_QUERY_PARAMS_FILE="${ROOT_DIR}/app/static/js/common/table-query-params.js"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，无法执行分页参数门禁检查。" >&2
  exit 1
fi

if [[ ! -f "${GRID_WRAPPER_FILE}" ]]; then
  echo "未找到 ${GRID_WRAPPER_FILE}，跳过检查。"
  exit 0
fi

LIMIT_QUERY_PARAM_PATTERN='limit='
PAGE_SIZE_QUERY_PARAM_PATTERN='page_size='

if "${RG_BIN}" -n "${PAGE_SIZE_QUERY_PARAM_PATTERN}" "${GRID_WRAPPER_FILE}"; then
  echo "" >&2
  echo "检测到 GridWrapper 使用 page_size= 作为分页参数，请统一改为 limit=。" >&2
  echo "规范参考：docs/Obsidian/standards/ui/gate/grid.md" >&2
  exit 1
fi

if ! "${RG_BIN}" -n "${LIMIT_QUERY_PARAM_PATTERN}" "${GRID_WRAPPER_FILE}" >/dev/null; then
  echo "" >&2
  echo "未检测到 GridWrapper 使用 limit=，请确认分页参数已统一。" >&2
  echo "规范参考：docs/Obsidian/standards/ui/gate/grid.md" >&2
  exit 1
fi

echo "✅ 分页参数门禁通过：GridWrapper 使用 limit。"

# --- TableQueryParams: 禁止 legacy page_size/pageSize，必须 normalize 为 limit ---

if [[ ! -f "${TABLE_QUERY_PARAMS_FILE}" ]]; then
  echo "未找到 ${TABLE_QUERY_PARAMS_FILE}，跳过 TableQueryParams 检查。"
  exit 0
fi

TABLE_FORBIDDEN_PATTERNS=(
  'readValue\s*\(\s*source\s*,\s*["\\x27]pageSize["\\x27]\s*\)'
  'readValue\s*\(\s*source\s*,\s*["\\x27]page_size["\\x27]\s*\)'
  '\bnormalized\.page_size\s*='
  '\bnormalized\.pageSize\s*='
  'pagination:legacy-page-size-param'
)

for pat in "${TABLE_FORBIDDEN_PATTERNS[@]}"; do
  if "${RG_BIN}" -n "${pat}" "${TABLE_QUERY_PARAMS_FILE}"; then
    echo "" >&2
    echo "检测到 TableQueryParams 仍在解析/输出 legacy page_size/pageSize（禁止）。" >&2
    echo "规范参考：docs/Obsidian/standards/ui/gate/grid.md" >&2
    exit 1
  fi
done

REQUIRED_PATTERNS=(
  'readValue\s*\(\s*source\s*,\s*["\\x27]limit["\\x27]\s*\)'
  '\bnormalized\.limit\b'
  '\bdelete\s+normalized\.page_size\b'
  '\bdelete\s+normalized\.pageSize\b'
)

for pat in "${REQUIRED_PATTERNS[@]}"; do
  if ! "${RG_BIN}" -n "${pat}" "${TABLE_QUERY_PARAMS_FILE}" >/dev/null; then
    echo "" >&2
    echo "TableQueryParams 缺少必要的 limit normalize 逻辑（pattern: ${pat}）。" >&2
    echo "规范参考：docs/Obsidian/standards/ui/gate/grid.md" >&2
    exit 1
  fi
done

echo "✅ 分页参数门禁通过：TableQueryParams 使用 limit 且已清理 legacy page_size/pageSize。"
