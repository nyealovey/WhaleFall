#!/usr/bin/env bash
# Sync current workspace code into a running Docker container for local verification.
#
# Default target is the production container name: whalefall_app_prod
#
# Examples:
#   ./scripts/dev/sync-local-code-to-docker.sh
#   ./scripts/dev/sync-local-code-to-docker.sh --container whalefall_app_prod
#   ./scripts/dev/sync-local-code-to-docker.sh --no-restart
#   ./scripts/dev/sync-local-code-to-docker.sh --dry-run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

CONTAINER_NAME="whalefall_app_prod"
TARGET_DIR="/app"
DRY_RUN=0
RESTART=1
RELOAD_NGINX=0
CHECK=1
TMP_DIR=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

cleanup() {
  if [[ -n "${TMP_DIR:-}" && -d "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
  fi
}

usage() {
  cat <<'EOF'
用法: ./scripts/dev/sync-local-code-to-docker.sh [选项]

选项:
  --container <name>    容器名(默认: whalefall_app_prod)
  --target <path>       容器内目标目录(默认: /app)
  --no-restart          仅拷贝，不重启 Gunicorn
  --reload-nginx        同步后重启 nginx(supervisor)
  --no-check            跳过 curl 快速检查
  --dry-run             仅展示将要同步的文件数量
  -h, --help            显示帮助

说明:
  - 脚本不会拉取代码，只会把当前工作区代码覆盖到容器的 /app 下
  - 默认会执行: supervisorctl restart whalefall
  - 不会同步: .git、.env、userdata、.venv 等目录(避免破坏数据/依赖)
EOF
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    log_error "未找到命令: ${cmd}"
    exit 1
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --container)
        CONTAINER_NAME="${2:-}"
        shift 2
        ;;
      --target)
        TARGET_DIR="${2:-}"
        shift 2
        ;;
      --no-restart)
        RESTART=0
        shift
        ;;
      --reload-nginx)
        RELOAD_NGINX=1
        shift
        ;;
      --no-check)
        CHECK=0
        shift
        ;;
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        log_error "未知参数: $1"
        usage
        exit 1
        ;;
    esac
  done

  if [[ -z "${CONTAINER_NAME}" ]]; then
    log_error "--container 不能为空"
    exit 1
  fi
  if [[ -z "${TARGET_DIR}" ]]; then
    log_error "--target 不能为空"
    exit 1
  fi
}

check_docker() {
  require_cmd docker
  if ! docker info >/dev/null 2>&1; then
    log_error "Docker 服务不可用，请先启动 Docker Desktop/daemon"
    exit 1
  fi

  if ! docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    log_error "未找到容器: ${CONTAINER_NAME}"
    exit 1
  fi

  local running
  running="$(docker inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || echo "false")"
  if [[ "${running}" != "true" ]]; then
    log_error "容器未运行: ${CONTAINER_NAME}"
    exit 1
  fi
}

stage_workspace() {
  local tmp_dir="$1"
  mkdir -p "${tmp_dir}"

  local -a dirs=(
    app
    migrations
    sql
    docs
    tests
    scripts
    nginx
    skills
  )

  for d in "${dirs[@]}"; do
    if [[ -d "${ROOT_DIR}/${d}" ]]; then
      cp -R "${ROOT_DIR}/${d}" "${tmp_dir}/"
    fi
  done

  shopt -s nullglob
  local -a root_globs=(
    "${ROOT_DIR}/"*.py
    "${ROOT_DIR}/"*.md
    "${ROOT_DIR}/"*.txt
    "${ROOT_DIR}/"*.toml
    "${ROOT_DIR}/"*.yml
    "${ROOT_DIR}/"*.yaml
    "${ROOT_DIR}/"*.ini
    "${ROOT_DIR}/"*.lock
    "${ROOT_DIR}/"Makefile*
    "${ROOT_DIR}/"package.json
    "${ROOT_DIR}/"package-lock.json
    "${ROOT_DIR}/"eslint.config.cjs
    "${ROOT_DIR}/"pyrightconfig.json
  )
  if (( ${#root_globs[@]} > 0 )); then
    cp -R "${root_globs[@]}" "${tmp_dir}/" 2>/dev/null || true
  fi
  shopt -u nullglob
}

clear_container_cache() {
  docker exec "${CONTAINER_NAME}" sh -lc "
    find ${TARGET_DIR} -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
    find ${TARGET_DIR} -name '*.pyc' -type f -delete 2>/dev/null || true
    find ${TARGET_DIR} -name '*.pyo' -type f -delete 2>/dev/null || true
    find ${TARGET_DIR} -name '.pytest_cache' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  "
}

ensure_gunicorn_conf() {
  docker exec "${CONTAINER_NAME}" sh -lc "
    if [ ! -f ${TARGET_DIR}/gunicorn.conf.py ] && [ -f ${TARGET_DIR}/nginx/gunicorn/gunicorn-prod.conf.py ]; then
      cp ${TARGET_DIR}/nginx/gunicorn/gunicorn-prod.conf.py ${TARGET_DIR}/gunicorn.conf.py
    fi
  "
}

restart_services() {
  docker exec "${CONTAINER_NAME}" supervisorctl restart whalefall
  if [[ "${RELOAD_NGINX}" -eq 1 ]]; then
    docker exec "${CONTAINER_NAME}" supervisorctl restart nginx
  fi
}

quick_check() {
  log_info "Quick check (inside container):"
  docker exec "${CONTAINER_NAME}" sh -lc '
    set -e
    check() {
      local path="$1"
      local code
      code="$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5001${path}" || true)"
      printf "  %-24s -> %s\n" "${path}" "${code}"
    }
    check "/health/api/basic"
    check "/api/v1/openapi.json"
    check "/api/v1/health/ping"
    check "/api/v1/"
  '
}

main() {
  parse_args "$@"
  check_docker

  trap cleanup EXIT

  TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/whalefall-local-sync.XXXXXX")"

  log_info "Staging workspace files..."
  stage_workspace "${TMP_DIR}"

  local file_count
  file_count="$(find "${TMP_DIR}" -type f | wc -l | tr -d ' ')"
  if [[ "${file_count}" == "0" ]]; then
    log_error "没有找到任何文件可同步(临时目录为空): ${TMP_DIR}"
    exit 1
  fi
  log_info "Staged files: ${file_count}"

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log_success "dry-run 完成(未写入容器)"
    return 0
  fi

  log_info "Clearing Python cache in container..."
  clear_container_cache

  log_info "Copying files into container: ${CONTAINER_NAME}:${TARGET_DIR}"
  docker cp "${TMP_DIR}/." "${CONTAINER_NAME}:${TARGET_DIR}/"
  ensure_gunicorn_conf

  if [[ "${RESTART}" -eq 1 ]]; then
    log_info "Restarting supervised processes..."
    restart_services
  else
    log_warning "已跳过重启(你需要手动 reload/restart 才会生效)"
  fi

  if [[ "${CHECK}" -eq 1 ]]; then
    quick_check
  fi

  log_success "同步完成"
  log_info "Host access: http://localhost:5001"
}

main "$@"
