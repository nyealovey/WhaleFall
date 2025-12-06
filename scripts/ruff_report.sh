#!/usr/bin/env bash

# Ruff 报告生成脚本
# 支持按模式选择规则、输出时间戳报告，并可选启用自动修复。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${ROOT_DIR}/docs/reports"
MODE="${1:-quick}"

TIMESTAMP="${TIMESTAMP:-$(date +%Y-%m-%d_%H%M%S)}"
mkdir -p "${REPORT_DIR}"

# 依据模式设定默认规则选择
case "${MODE}" in
  quick)
    DEFAULT_SELECT="F401,F841,F811"        # 未使用导入/变量/重复定义
    ;;
  style)
    DEFAULT_SELECT="D,I,PLC,G"             # Docstring/导入/顶层导入/日志格式
    ;;
  security)
    DEFAULT_SELECT="S1,S104,S105,S110"     # 常见安全规则与网络绑定
    ;;
  full)
    DEFAULT_SELECT="ALL"
    ;;
  *)
    # 自定义模式：允许通过 RUFF_SELECT 传入
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

REPORT_FILE="${REPORT_DIR}/ruff_${MODE}_${TIMESTAMP}.txt"

echo "运行 Ruff 模式: ${MODE}"
[[ -n "${SELECT}" ]] && echo "规则选择: ${SELECT}" || echo "规则选择: 默认"
echo "报告输出: ${REPORT_FILE}"

cd "${ROOT_DIR}"

# shellcheck disable=SC2086
ruff check . ${SELECT:+--select "${SELECT}"} ${FIX_FLAG} ${RUFF_EXTRA_ARGS:-} | tee "${REPORT_FILE}"

echo "完成。报告已保存到 ${REPORT_FILE}"
