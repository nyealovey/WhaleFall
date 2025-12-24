#!/usr/bin/env bash
# 危险按钮语义门禁：禁止用 text-danger 伪装危险按钮（必须使用 btn-outline-danger/btn-danger 等语义按钮）

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE_DIR="${ROOT_DIR}/app/templates"
JS_DIR="${ROOT_DIR}/app/static/js"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，无法执行危险按钮语义门禁检查。" >&2
  exit 1
fi

TARGETS=()
if [[ -d "${TEMPLATE_DIR}" ]]; then
  TARGETS+=("${TEMPLATE_DIR}")
fi
if [[ -d "${JS_DIR}" ]]; then
  TARGETS+=("${JS_DIR}")
fi

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo "未找到 app/templates 或 app/static/js，跳过检查。"
  exit 0
fi

# 说明：
# - 禁止用 `text-danger` 叠加在次按钮/图标按钮上“伪装危险按钮”，这会导致同类危险操作在不同页面呈现不一致。
# - 危险操作触发按钮必须选择语义按钮：不可撤销/删除类优先 `btn-outline-danger`（必要时 `btn-danger`）。
PATTERN_OUTLINE_SECONDARY_TEXT_DANGER='<(button|a)[^>]*\bclass\s*=\s*[^>]*(btn-outline-secondary[^>]*text-danger|text-danger[^>]*btn-outline-secondary)'
PATTERN_BTN_ICON_TEXT_DANGER='<(button|a)[^>]*\bclass\s*=\s*[^>]*(btn-icon[^>]*text-danger|text-danger[^>]*btn-icon)'

FOUND=0
if "${RG_BIN}" -n -U "${PATTERN_OUTLINE_SECONDARY_TEXT_DANGER}" "${TARGETS[@]}"; then
  FOUND=1
fi
if "${RG_BIN}" -n -U "${PATTERN_BTN_ICON_TEXT_DANGER}" "${TARGETS[@]}"; then
  FOUND=1
fi

if [[ "${FOUND}" -eq 1 ]]; then
  echo "" >&2
  echo "检测到危险按钮语义反模式：" >&2
  echo "- 在 button/a 上使用了 btn-outline-secondary + text-danger 或 btn-icon + text-danger。" >&2
  echo "" >&2
  echo "修复建议：" >&2
  echo "- 删除/不可撤销：触发按钮使用 btn btn-outline-danger（必要时 btn btn-danger）。" >&2
  echo "- 仅图标危险按钮：使用 btn btn-outline-danger btn-icon，并移除 text-danger。" >&2
  echo "- 二次确认统一使用 UI.confirmDanger(options)，删除类 confirmButtonClass 使用 btn-danger。" >&2
  exit 1
fi

echo "✅ 危险按钮语义门禁通过：未发现 text-danger 伪装危险按钮。"

