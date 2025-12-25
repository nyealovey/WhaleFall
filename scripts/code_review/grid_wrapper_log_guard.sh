#!/usr/bin/env bash
# GridWrapper 日志门禁：禁止在 grid-wrapper.js 内常驻 console.log

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_FILE="${ROOT_DIR}/app/static/js/common/grid-wrapper.js"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，无法执行 GridWrapper 日志门禁检查。" >&2
  exit 1
fi

if [[ ! -f "${TARGET_FILE}" ]]; then
  echo "未找到 ${TARGET_FILE}，跳过检查。"
  exit 0
fi

CONSOLE_LOG_PATTERN='\\bconsole\\.log\\b'

if "${RG_BIN}" -n "${CONSOLE_LOG_PATTERN}" "${TARGET_FILE}"; then
  echo "" >&2
  echo "检测到 GridWrapper 内存在 console.log，请改为受开关控制的 console.debug（或直接删除）。" >&2
  echo "规范参考：docs/standards/ui/grid-wrapper-performance-logging-guidelines.md" >&2
  exit 1
fi

echo "✅ GridWrapper 日志门禁通过：未发现 console.log。"

