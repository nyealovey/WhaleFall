#!/usr/bin/env bash
# CSS Token 门禁：防止 var(--xxx) 引用未定义的 CSS 变量，造成样式回退/漂移
#
# 参考：
# - docs/Obsidian/standards/ui/gate/design-token-governance.md

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${ROOT_DIR}/app/static/css"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，无法执行 CSS Token 门禁检查。" >&2
  exit 1
fi

if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "未找到 ${TARGET_DIR}，跳过检查。"
  exit 0
fi

# 说明：
# - 检查 app/static/css 下所有 .css（不含 vendor）中是否存在 var(--xxx) 引用但没有任何 --xxx: 定义。
# - 允许使用外部变量（如 Bootstrap 的 --bs-*），此类前缀会被忽略。
ALLOW_PREFIX_REGEX='^--bs-'

refs="$("${RG_BIN}" -o --no-filename -- "var\\(--[A-Za-z0-9_-]+" "${TARGET_DIR}" | sed 's/var(//' | sort -u || true)"
defs="$("${RG_BIN}" -o --no-filename -- "--[A-Za-z0-9_-]+:" "${TARGET_DIR}" | sed 's/:$//' | sort -u || true)"

unknown="$(comm -23 <(printf "%s\n" "${refs}") <(printf "%s\n" "${defs}") || true)"
unknown="$(printf "%s\n" "${unknown}" | grep -Ev "${ALLOW_PREFIX_REGEX}" || true)"

if [[ -n "${unknown}" ]]; then
  echo "" >&2
  echo "检测到未定义的 CSS Token（存在 var(--xxx) 引用，但未找到 --xxx: 定义）：" >&2
  echo "" >&2
  printf "%s\n" "${unknown}" | sed 's/^/- /' >&2
  echo "" >&2
  echo "修复建议：" >&2
  echo "- 如果是全站设计 Token，请在 app/static/css/variables.css 中补齐定义。" >&2
  echo "- 如果是局部组件变量，请在对应组件/页面 CSS 中补齐 --xxx: 定义，并确保命名不与全局 Token 冲突。" >&2
  echo "参考：docs/Obsidian/standards/ui/gate/design-token-governance.md" >&2
  exit 1
fi

echo "✅ CSS Token 门禁通过：未发现未定义的 CSS var token。"
