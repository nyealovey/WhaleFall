#!/usr/bin/env bash
# 写操作边界门禁：禁止 routes 直写 db.session（add/delete/commit/flush）

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${ROOT_DIR}/app/routes"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，请先安装 ripgrep，或设置 RG_BIN 指向可执行文件。" >&2
  exit 1
fi

if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "未找到 ${TARGET_DIR}，跳过检查。"
  exit 0
fi

PATTERN="db\\.session\\.(add|add_all|delete|commit|flush)\\("

hits="$("${RG_BIN}" -n --hidden --type py "${PATTERN}" "${TARGET_DIR}" || true)"
if [[ -n "${hits}" ]]; then
  echo "检测到 routes 直写 db.session（禁止）：" >&2
  echo "${hits}" >&2
  echo "" >&2
  echo "请将写操作收敛到：routes -> WriteService -> Repository(add/delete/flush)，并由 safe_route_call 统一提交事务。" >&2
  echo "参考：docs/changes/refactor/002-backend-write-operation-boundary-plan.md" >&2
  exit 1
fi

echo "✅ 写操作边界门禁通过：routes 未直写 db.session 写操作。"
