#!/usr/bin/env bash
# btn-close 可访问名称门禁：禁止缺失 aria-label 或使用英文 Close
#
# 参考：
# - docs/Obsidian/standards/ui/gate/close-button-accessible-name.md

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGETS=(
  "${ROOT_DIR}/app/templates"
  "${ROOT_DIR}/app/static/js"
)

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，无法执行 btn-close aria-label 门禁检查。" >&2
  exit 1
fi

# 说明：
# - 关闭按钮必须有可访问名称，读屏才能读出“关闭”。
# - 禁止使用英文 Close，避免读屏语言混用。

BTN_CLOSE_BUTTON_PATTERN='<button[^>]*\bbtn-close\b[^>]*>'

MISSING_ARIA_LABEL_PATTERN='aria-label='

ENGLISH_ARIA_LABEL_PATTERN='aria-label=("Close"|'\''Close'\'')'

if "${RG_BIN}" -n "${ENGLISH_ARIA_LABEL_PATTERN}" "${TARGETS[@]}"; then
  echo "" >&2
  echo "检测到 btn-close 使用英文 aria-label=Close，请统一为中文 aria-label=\"关闭\"。" >&2
  echo "参考：docs/Obsidian/standards/ui/gate/close-button-accessible-name.md" >&2
  exit 1
fi

if "${RG_BIN}" -n "${BTN_CLOSE_BUTTON_PATTERN}" "${TARGETS[@]}" | "${RG_BIN}" -n -v "${MISSING_ARIA_LABEL_PATTERN}"; then
  echo "" >&2
  echo "检测到 btn-close 缺失 aria-label，请补充 aria-label=\"关闭\"。" >&2
  echo "参考：docs/Obsidian/standards/ui/gate/close-button-accessible-name.md" >&2
  exit 1
fi

echo "✅ btn-close aria-label 门禁通过：未发现缺失/英文混用。"
