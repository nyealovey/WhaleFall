#!/usr/bin/env bash
# Ruff 报告生成脚本：依据模式运行 ruff lint，并保存报告到 docs/reports

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${ROOT_DIR}/docs/reports"
MODE="${1:-quick}"

TIMESTAMP="${TIMESTAMP:-$(date +%Y-%m-%d_%H%M%S)}"
mkdir -p "${REPORT_DIR}"

RUFF_BIN="${RUFF_BIN:-ruff}"
if ! command -v "${RUFF_BIN}" >/dev/null 2>&1; then
  if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/ruff" ]]; then
    RUFF_BIN="${VIRTUAL_ENV}/bin/ruff"
  elif [[ -x "${ROOT_DIR}/.venv/bin/ruff" ]]; then
    RUFF_BIN="${ROOT_DIR}/.venv/bin/ruff"
  else
    echo "未检测到 ruff 命令，请先执行 make install/uv sync 安装依赖，或设置 RUFF_BIN 指向可执行文件。" >&2
    exit 1
  fi
fi

case "${MODE}" in
  quick)
    DEFAULT_SELECT="F401,F841,F811"
    ;;
  style)
    DEFAULT_SELECT="D,I,PLC,G"
    ;;
  security)
    DEFAULT_SELECT="S1,S104,S105,S110"
    ;;
  full)
    DEFAULT_SELECT="ALL"
    ;;
  *)
    DEFAULT_SELECT=""
    ;;
esac

# 允许通过环境变量覆盖规则选择
SELECT="${RUFF_SELECT:-${DEFAULT_SELECT}}"

# 允许开启自动修复
FIX_FLAG=""
if [[ "${FIX:-false}" == "true" ]]; then
  FIX_FLAG="--fix"
fi

# 允许打开 unsafe-fixes
UNSAFE_FLAG=""
if [[ "${UNSAFE:-false}" == "true" ]]; then
  UNSAFE_FLAG="--unsafe-fixes"
fi

REPORT_FILE="${REPORT_DIR}/ruff_${MODE}_${TIMESTAMP}.txt"

echo "运行 Ruff 模式: ${MODE}"
[[ -n "${SELECT}" ]] && echo "规则选择: ${SELECT}" || echo "规则选择: 默认"
[[ "${FIX:-false}" == "true" ]] && echo "自动修复: 开启 (--fix)" || echo "自动修复: 关闭"
[[ "${UNSAFE:-false}" == "true" ]] && echo "Unsafe fixes: 开启 (--unsafe-fixes)" || echo "Unsafe fixes: 关闭"
echo "报告输出: ${REPORT_FILE}"

cd "${ROOT_DIR}"

# shellcheck disable=SC2086
"${RUFF_BIN}" check . ${SELECT:+--select "${SELECT}"} ${FIX_FLAG} ${UNSAFE_FLAG} ${RUFF_EXTRA_ARGS:-} | tee "${REPORT_FILE}"

echo "完成。报告已保存到 ${REPORT_FILE}"
