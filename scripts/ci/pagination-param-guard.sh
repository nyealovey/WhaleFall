#!/usr/bin/env bash
# 分页参数门禁：GridWrapper 必须使用 limit 作为分页大小参数

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GRID_WRAPPER_FILE="${ROOT_DIR}/app/static/js/common/grid-wrapper.js"

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
