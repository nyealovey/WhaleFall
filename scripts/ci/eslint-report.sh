#!/usr/bin/env bash
# ESLint 报告脚本：运行 eslint 并将输出保存到 docs/reports
#
# 参考：
# - docs/Obsidian/standards/core/guide/scripts.md
# - docs/Obsidian/standards/core/guide/coding.md
# - docs/Obsidian/standards/ui/design/javascript-module.md

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${ROOT_DIR}/docs/reports"
MODE="${1:-quick}"
TIMESTAMP="${TIMESTAMP:-$(date +%Y-%m-%d_%H%M%S)}"
REPORT_FILE="${REPORT_DIR}/eslint_${MODE}_${TIMESTAMP}.txt"
TARGET_PATH="${ESLINT_TARGET:-app/static/js}"
ESLINT_EXTS="${ESLINT_EXTS:-.js}"

mkdir -p "${REPORT_DIR}"

ESLINT_CMD=()

if [[ -n "${ESLINT_BIN:-}" && -x "${ESLINT_BIN}" ]]; then
  ESLINT_CMD=("${ESLINT_BIN}")
elif command -v eslint >/dev/null 2>&1; then
  ESLINT_CMD=("eslint")
elif [[ -x "${ROOT_DIR}/node_modules/.bin/eslint" ]]; then
  ESLINT_CMD=("${ROOT_DIR}/node_modules/.bin/eslint")
elif command -v npx >/dev/null 2>&1; then
  ESLINT_CMD=("npx" "eslint")
else
  echo "未检测到 eslint 命令，请运行 npm install / make install 安装依赖，或设置 ESLINT_BIN 指向可执行文件。" >&2
  exit 1
fi

DEFAULT_ARGS=()
case "${MODE}" in
  quick)
    DEFAULT_ARGS=("--max-warnings" "0" "--quiet")
    ;;
  full)
    DEFAULT_ARGS=()
    ;;
  *)
    DEFAULT_ARGS=()
    ;;
esac

EXTRA_ARGS=()
if [[ -n "${ESLINT_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  EXTRA_ARGS=(${ESLINT_EXTRA_ARGS})
fi

FIX_FLAG=()
if [[ "${FIX:-false}" == "true" ]]; then
  FIX_FLAG=("--fix")
fi

CMD=("${ESLINT_CMD[@]}" "${TARGET_PATH}" "--ext" "${ESLINT_EXTS}" "${DEFAULT_ARGS[@]:-}" "${FIX_FLAG[@]:-}")

if ((${#EXTRA_ARGS[@]})); then
  CMD+=("${EXTRA_ARGS[@]}")
fi

CLEAN_CMD=()
for arg in "${CMD[@]}"; do
  [[ -n "${arg}" ]] && CLEAN_CMD+=("${arg}")
done

if [[ ${#CLEAN_CMD[@]} -eq 0 ]]; then
  echo "未构建 eslint 命令，请检查参数。" >&2
  exit 1
fi

printf '运行 ESLint 命令: %s\n' "${CLEAN_CMD[*]}"
printf '报告输出: %s\n' "${REPORT_FILE}"

cd "${ROOT_DIR}"

if "${CLEAN_CMD[@]}" | tee "${REPORT_FILE}"; then
  printf '✅ ESLint 完成，报告位于 %s\n' "${REPORT_FILE}"
else
  status=$?
  printf 'ESLint 运行失败 (exit %s)，请查看报告文件以排查。\n' "${status}" >&2
  exit "${status}"
fi
