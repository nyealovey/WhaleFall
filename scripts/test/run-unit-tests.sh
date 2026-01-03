#!/usr/bin/env bash
# 运行单元测试（自动准备测试环境与清理临时数据）
#
# 用法: ./scripts/test/run-unit-tests.sh [选项] [pytest 参数...]
#
# 选项:
#   --init-env          初始化 .env.test.local（如不存在）
#   --force-init-env    覆盖写入 .env.test.local
#   --keep-temp         保留临时目录（调试用）
#   --no-sync           跳过 uv sync（依赖已就绪时可用）
#   --help, -h          显示帮助信息
#
# 示例:
#   ./scripts/test/run-unit-tests.sh
#   ./scripts/test/run-unit-tests.sh -k capacity
#   ./scripts/test/run-unit-tests.sh -- --maxfail=1

set -euo pipefail

# ============================================================
# 常量定义
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.test.local"

KEEP_TEMP=0
TMP_DIR=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================
# 日志函数
# ============================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# ============================================================
# 帮助信息
# ============================================================
show_usage() {
    echo "用法: $0 [选项] [pytest 参数...]"
    echo ""
    echo "选项:"
    echo "  --init-env          初始化 .env.test.local（如不存在）"
    echo "  --force-init-env    覆盖写入 .env.test.local"
    echo "  --keep-temp         保留临时目录（调试用）"
    echo "  --no-sync           跳过 uv sync（依赖已就绪时可用）"
    echo "  --help, -h          显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0"
    echo "  $0 -k capacity"
    echo "  $0 -- --maxfail=1"
}

# ============================================================
# .env 生成
# ============================================================
write_env_file() {
    local tmp_file
    tmp_file="$(mktemp "${ENV_FILE}.XXXXXX")"

    cat >"${tmp_file}" <<'EOF'
# WhaleFall 测试环境配置（本地）
#
# 说明:
# - 本文件仅用于本机测试，不要提交到仓库（已在 .gitignore 中忽略）
# - 推荐使用脚本运行单元测试：./scripts/test/run-unit-tests.sh
#
# 调整建议:
# - 单测默认不依赖 Redis/外部数据库；如需调试可自行修改

# Flask 环境
FLASK_ENV=testing
FLASK_DEBUG=0

# 单元测试默认使用内存 SQLite
DATABASE_URL=sqlite:///:memory:

# 缓存：单测默认使用 simple，避免依赖 Redis
CACHE_TYPE=simple
CACHE_REDIS_URL=redis://localhost:6379/0

# 安全密钥（仅测试用途）
SECRET_KEY=test-secret-key
JWT_SECRET_KEY=test-jwt-key

# 测试加速（bcrypt rounds 最小允许值为 4）
BCRYPT_LOG_ROUNDS=4
LOG_LEVEL=WARNING
EOF

    mv "${tmp_file}" "${ENV_FILE}"
    chmod 600 "${ENV_FILE}" 2>/dev/null || true
}

ensure_env_file() {
    local force_init="${1}"

    if [[ -f "${ENV_FILE}" && "${force_init}" -eq 0 ]]; then
        return
    fi

    write_env_file
    log_success "已生成测试环境文件: ${ENV_FILE}"
    log_warning "如需调整测试配置，请编辑 ${ENV_FILE}（脚本不会覆盖你的修改）"
}

# ============================================================
# 主逻辑
# ============================================================
main() {
    local init_env_only=0
    local force_init_env=0
    local no_sync=0
    local -a pytest_args=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                show_usage
                exit 0
                ;;
            --init-env)
                init_env_only=1
                shift
                ;;
            --force-init-env)
                force_init_env=1
                shift
                ;;
            --keep-temp)
                KEEP_TEMP=1
                shift
                ;;
            --no-sync)
                no_sync=1
                shift
                ;;
            --)
                shift
                pytest_args+=("$@")
                break
                ;;
            *)
                pytest_args+=("$1")
                shift
                ;;
        esac
    done

    ensure_env_file "${force_init_env}"
    if [[ "${init_env_only}" -eq 1 ]]; then
        exit 0
    fi

    if ! command -v uv >/dev/null 2>&1; then
        log_error "未找到 uv，请先安装（例如: brew install uv）"
        exit 1
    fi

    cd "${ROOT_DIR}"

    if [[ "${no_sync}" -eq 0 ]]; then
        log_info "同步依赖（dev group）..."
        uv sync --group dev
    fi

    TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/whalefall-unit-tests.XXXXXX")"

    local run_env_file="${TMP_DIR}/.env.test.run"
    cat "${ENV_FILE}" > "${run_env_file}"
    cat >> "${run_env_file}" <<EOF

# 自动生成：本次运行的临时目录（用于清理测试产生的数据）
LOG_FILE=${TMP_DIR}/app.log
EOF

    cleanup() {
        local exit_code=$?
        trap - EXIT
        set +e
        if [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]]; then
            if [[ "${KEEP_TEMP}" -eq 1 ]]; then
                log_warning "保留临时目录（keep-temp 已开启）: ${TMP_DIR}"
            else
                rm -rf "${TMP_DIR}"
            fi
        fi
        exit "${exit_code}"
    }
    trap cleanup EXIT

    log_info "运行单元测试..."
    uv run --env-file "${run_env_file}" pytest -m unit "${pytest_args[@]+"${pytest_args[@]}"}"
    log_success "单元测试通过"
}

main "$@"
