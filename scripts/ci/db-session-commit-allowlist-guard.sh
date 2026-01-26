#!/usr/bin/env bash
# db.session.commit 全局门禁：只允许在事务边界入口调用（routes/tasks/worker/scripts）
#
# 参考：
# - docs/Obsidian/standards/backend/standard/write-operation-boundary.md

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，请先安装 ripgrep，或设置 RG_BIN 指向可执行文件。" >&2
  exit 1
fi

cd "${ROOT_DIR}"

PATTERN="db\\.session\\.commit\\("

# 仅扫描 Python 文件，避免 baseline 等文本误报
hits="$("${RG_BIN}" -n --hidden --type py "${PATTERN}" app scripts || true)"
if [[ -z "${hits}" ]]; then
  echo "✅ commit allowlist 门禁通过：未发现 db.session.commit。"
  exit 0
fi

# 允许位置：
# - routes: 由 safe_route_call 承担提交（routes 自身禁止 commit）
# - tasks/scripts/worker: 入口可自行管理事务
# - infra: safe_route_call / queue worker
allowed_regex='^(app/infra/route_safety\.py:|app/infra/logging/queue_worker\.py:|app/tasks/|scripts/)'

unexpected="$(echo "${hits}" | LC_ALL=C sort | grep -v -E "${allowed_regex}" || true)"
if [[ -n "${unexpected}" ]]; then
  echo "检测到非事务边界入口的 db.session.commit（禁止）：" >&2
  echo "${unexpected}" >&2
  echo "" >&2
  echo "请将 commit 收敛到事务边界入口（safe_route_call / tasks / worker / scripts），services 仅使用 flush/savepoint。" >&2
  echo "参考：docs/Obsidian/standards/backend/standard/write-operation-boundary.md" >&2
  exit 1
fi

count="$(echo "${hits}" | wc -l | tr -d '[:space:]')"
echo "✅ commit allowlist 门禁通过：命中 ${count}（均位于允许位置）。"
