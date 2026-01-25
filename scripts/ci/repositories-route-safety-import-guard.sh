#!/usr/bin/env bash
# Repository 门禁：禁止依赖 app.infra.route_safety（避免仓储层引入 request/actor 语义）
#
# 参考：
# - docs/Obsidian/standards/backend/gate/layer/repository-layer.md
# - docs/Obsidian/standards/backend/gate/layer/infra-layer.md

set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  ./scripts/ci/repositories-route-safety-import-guard.sh

Checks:
  - app/repositories/**/*.py 禁止引用/导入 app.infra.route_safety
EOF
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，无法执行 repository route_safety 门禁检查。" >&2
  exit 1
fi

TARGET_DIR="app/repositories"
if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "未找到 ${TARGET_DIR}，跳过检查。"
  exit 0
fi

PATTERN='\\bapp\\.infra\\.route_safety\\b'

hits="$("${RG_BIN}" -n --hidden --type py -- "${PATTERN}" "${TARGET_DIR}" || true)"
if [[ -n "${hits}" ]]; then
  echo "检测到 repository 层依赖 app.infra.route_safety（禁止）：" >&2
  echo "${hits}" >&2
  echo "" >&2
  echo "Repository 仅负责数据访问与 Query 组装；事务边界与 request/actor 语义应停留在 routes/infra 边界。" >&2
  echo "参考：" >&2
  echo "- docs/Obsidian/standards/backend/gate/layer/repository-layer.md" >&2
  echo "- docs/Obsidian/standards/backend/gate/layer/infra-layer.md" >&2
  exit 1
fi

echo "✅ repository route_safety 门禁通过。"

