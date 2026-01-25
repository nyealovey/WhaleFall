#!/usr/bin/env bash
# Ops 门禁：防止运维/部署脚本回归旧路径与迁移残留
#
# 参考：
# - docs/Obsidian/operations/deployment/deployment-guide.md
# - docs/Obsidian/operations/deployment/production-deployment.md

set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  ./scripts/ci/ops-legacy-guard.sh

Checks:
  - 禁止出现旧健康检查路径：/health/api/
  - 禁止保留 userdata->volume 迁移脚本/Makefile target（历史迁移期残留）
EOF
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，无法执行 ops legacy 门禁检查。" >&2
  exit 1
fi

# --- 1) legacy health api paths ---

LEGACY_HEALTH_API_PREFIX="/health/api/"

TARGETS=(
  "Dockerfile.prod"
  "docker-compose.prod.yml"
  "docker-compose.flask-only.yml"
  "Makefile.prod"
  "Makefile.flask"
  "nginx"
  "scripts"
  "docs/operations"
)

existing_targets=()
for t in "${TARGETS[@]}"; do
  [[ -e "${t}" ]] && existing_targets+=("${t}")
done

if ((${#existing_targets[@]})); then
  # 排除 scripts/ci：门禁脚本自身会包含“旧路径”字面量（用于说明/变量），不应被扫描目标命中。
  hits="$(
    "${RG_BIN}" -n --hidden --glob '!scripts/ci/**' -- "${LEGACY_HEALTH_API_PREFIX}" "${existing_targets[@]}" || true
  )"
  if [[ -n "${hits}" ]]; then
    echo "发现旧健康检查 API 路径引用(将导致 410)：" >&2
    echo "${hits}" >&2
    echo "" >&2
    echo "请统一改为 /api/v1/health/*，参考部署文档：" >&2
    echo "- docs/Obsidian/operations/deployment/deployment-guide.md" >&2
    echo "- docs/Obsidian/operations/deployment/production-deployment.md" >&2
    exit 1
  fi
fi

# --- 2) legacy userdata->volume migration remnants ---

VOLUME_MANAGER_SCRIPT="scripts/ops/docker/volume_manager.sh"
if [[ -f "${VOLUME_MANAGER_SCRIPT}" ]]; then
  # 仅阻断“迁移期残留命令/函数/文案”，不阻断正常的 volume 管理能力。
  LEGACY_MARKERS=(
    "从userdata迁移到卷"
    "migrate [dev|prod]"
    "migrate dev --force"
    "migrate_volumes()"
    "./userdata"
  )
  for marker in "${LEGACY_MARKERS[@]}"; do
    if "${RG_BIN}" -n --fixed-strings -- "${marker}" "${VOLUME_MANAGER_SCRIPT}"; then
      echo "" >&2
      echo "发现 userdata->volume 迁移脚本残留（禁止）: ${marker}" >&2
      echo "文件: ${VOLUME_MANAGER_SCRIPT}" >&2
      exit 1
    fi
  done
fi

MAKEFILE_PROD="Makefile.prod"
if [[ -f "${MAKEFILE_PROD}" ]]; then
  LEGACY_MAKE_MARKERS=(
    "migrate-volumes:"
    "volume_manager.sh migrate"
    "迁移数据到卷"
  )
  for marker in "${LEGACY_MAKE_MARKERS[@]}"; do
    if "${RG_BIN}" -n --fixed-strings -- "${marker}" "${MAKEFILE_PROD}"; then
      echo "" >&2
      echo "发现 migrate-volumes 残留（禁止）: ${marker}" >&2
      echo "文件: ${MAKEFILE_PROD}" >&2
      exit 1
    fi
  done
fi

echo "✅ ops legacy 门禁通过。"
