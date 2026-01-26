#!/usr/bin/env bash
# Pyright 报告脚本：运行 pyright 并将输出保存到 docs/reports
#
# 参考：
# - docs/Obsidian/standards/core/guide/scripts.md
# - docs/Obsidian/standards/core/guide/coding.md

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${ROOT_DIR}/docs/reports"
TIMESTAMP="${TIMESTAMP:-$(date +%Y-%m-%d_%H%M%S)}"
REPORT_FILE="${REPORT_DIR}/pyright_full_${TIMESTAMP}.txt"

mkdir -p "${REPORT_DIR}"

PYRIGHT_BIN="${PYRIGHT_BIN:-pyright}"
PYRIGHT_CMD=()

if command -v "${PYRIGHT_BIN}" >/dev/null 2>&1; then
  PYRIGHT_CMD=("${PYRIGHT_BIN}")
elif [[ -x "${ROOT_DIR}/node_modules/.bin/pyright" ]]; then
  PYRIGHT_CMD=("${ROOT_DIR}/node_modules/.bin/pyright")
elif [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/pyright" ]]; then
  PYRIGHT_CMD=("${VIRTUAL_ENV}/bin/pyright")
elif command -v uv >/dev/null 2>&1; then
  echo "未找到 pyright 可执行文件，改用 uv tool run pyright." >&2
  PYRIGHT_CMD=("uv" "tool" "run" "pyright")
else
  echo "未检测到 pyright 命令，请通过 npm/uv 安装，或设置 PYRIGHT_BIN 指向可执行文件。" >&2
  exit 1
fi

EXTRA_ARGS=()
if [[ -n "${PYRIGHT_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  EXTRA_ARGS=(${PYRIGHT_EXTRA_ARGS})
fi

CMD=("${PYRIGHT_CMD[@]}")

if ((${#EXTRA_ARGS[@]})); then
  CMD+=("${EXTRA_ARGS[@]}")
fi

if [[ $# -gt 0 ]]; then
  CMD+=("$@")
else
  CMD+=("--project" "pyrightconfig.json")
fi

CLEAN_CMD=()
for arg in "${CMD[@]}"; do
  [[ -n "${arg}" ]] && CLEAN_CMD+=("${arg}")
done

if [[ ${#CLEAN_CMD[@]} -eq 0 ]]; then
  echo "未构建 pyright 命令，请检查参数。" >&2
  exit 1
fi

printf '运行 Pyright 命令: %s\n' "${CLEAN_CMD[*]}"
printf '报告输出: %s\n' "${REPORT_FILE}"

cd "${ROOT_DIR}"

if "${CLEAN_CMD[@]}" | tee "${REPORT_FILE}"; then
  printf '✅ Pyright 完成，报告位于 %s\n' "${REPORT_FILE}"
else
  status=$?
  printf 'Pyright 运行失败 (exit %s)，请查看报告文件以排查。\n' "${status}" >&2
  exit "${status}"
fi
