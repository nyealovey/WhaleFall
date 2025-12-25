#!/usr/bin/env bash
# 按钮层级门禁：防止通过全局 border 覆盖破坏 Bootstrap outline 按钮语义

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${ROOT_DIR}/app/static/css"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，无法执行按钮层级门禁检查。" >&2
  exit 1
fi

if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "未找到 ${TARGET_DIR}，跳过检查。"
  exit 0
fi

# 说明：
# - Bootstrap 的 btn-outline-* 依赖 border 呈现按钮边界。
# - `.btn { border: none; }` 会让 outline/次按钮退化成“看起来像文本/标签”，削弱层级并增加误点风险。
BTN_BORDER_KILL_PATTERN='\.btn\s*\{[^}]*\bborder\s*:\s*(none|0(px)?)\b'

if "${RG_BIN}" -n -U "${BTN_BORDER_KILL_PATTERN}" "${TARGET_DIR}"; then
  echo "" >&2
  echo "检测到对 .btn 的 border 破坏性覆盖（border: none/0）。" >&2
  echo "这会直接破坏 btn-outline-* 的描边体系，导致次按钮“不像按钮”。" >&2
  echo "" >&2
  echo "修复建议：" >&2
  echo "- 不要在 .btn 上禁用 border；如需特殊外观请使用更具体的容器/组件类。" >&2
  echo "- 如确需对某一类按钮移除边框，请限定到语义类（例如 .btn-primary）或容器作用域，并确保不影响 btn-outline-*。" >&2
  exit 1
fi

echo "✅ 按钮层级门禁通过：未发现 .btn 的 border:none/0 覆盖。"
