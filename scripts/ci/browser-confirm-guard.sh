#!/usr/bin/env bash
# 浏览器 confirm 门禁：禁止在前端使用 window.confirm/global.confirm/confirm 弹窗
#
# 参考：
# - docs/Obsidian/standards/ui/gate/danger-operation-confirmation.md

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${ROOT_DIR}/app/static/js"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，无法执行浏览器 confirm 门禁检查。" >&2
  exit 1
fi

if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "未找到 ${TARGET_DIR}，跳过检查。"
  exit 0
fi

# 说明：
# - 浏览器 confirm 会破坏全站体验一致性（样式不可控、文案/按钮不可统一、无法展示影响范围/结果入口）。
# - 全站统一使用 `UI.confirmDanger(options)`。
WINDOW_CONFIRM_PATTERN='\bwindow\.confirm\s*\('
GLOBAL_CONFIRM_PATTERN='\bglobal\.confirm\s*\('
# 仅拦截“直接调用 confirm(...)”，避免误伤类似 obj.confirm(...)
PLAIN_CONFIRM_PATTERN='(^|[^.\w])confirm\s*\('

if "${RG_BIN}" -n "${WINDOW_CONFIRM_PATTERN}" "${TARGET_DIR}"; then
  echo "" >&2
  echo "检测到 window.confirm 调用，请改用 UI.confirmDanger(options)。" >&2
  echo "参考：docs/Obsidian/standards/ui/gate/danger-operation-confirmation.md" >&2
  exit 1
fi

if "${RG_BIN}" -n "${GLOBAL_CONFIRM_PATTERN}" "${TARGET_DIR}"; then
  echo "" >&2
  echo "检测到 global.confirm 调用，请改用 UI.confirmDanger(options)。" >&2
  echo "参考：docs/Obsidian/standards/ui/gate/danger-operation-confirmation.md" >&2
  exit 1
fi

if "${RG_BIN}" -n "${PLAIN_CONFIRM_PATTERN}" "${TARGET_DIR}"; then
  echo "" >&2
  echo "检测到 confirm(...) 调用，请改用 UI.confirmDanger(options)。" >&2
  echo "参考：docs/Obsidian/standards/ui/gate/danger-operation-confirmation.md" >&2
  exit 1
fi

echo "✅ 浏览器 confirm 门禁通过：未发现 confirm 弹窗调用。"
