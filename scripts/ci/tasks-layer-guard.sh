#!/usr/bin/env bash
# Tasks 层门禁：禁止 tasks 直查库/直写库（允许 commit/rollback 作为事务边界入口）

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${ROOT_DIR}/app/tasks"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，请先安装 ripgrep，或设置 RG_BIN 指向可执行文件。" >&2
  exit 1
fi

if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "未找到 ${TARGET_DIR}，跳过检查。"
  exit 0
fi

PATTERN="\\.query\\b|db\\.session\\.(query|execute|add|add_all|delete|merge|flush)\\("

hits="$("${RG_BIN}" -n --hidden --type py "${PATTERN}" "${TARGET_DIR}" || true)"
if [[ -n "${hits}" ]]; then
  echo "检测到 tasks 层直查库/直写库（禁止）：" >&2
  echo "${hits}" >&2
  echo "" >&2
  echo "Tasks 只允许做调度入口与可观测性；查库/写库应下沉到 Service/Repository（tasks 仅可 commit/rollback 作为边界）。" >&2
  echo "参考：docs/Obsidian/standards/backend/gate/layer/tasks-layer.md" >&2
  exit 1
fi

echo "✅ Tasks 层门禁通过：未发现 query/execute/add/delete/merge/flush。"
