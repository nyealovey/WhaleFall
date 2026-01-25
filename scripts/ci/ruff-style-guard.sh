#!/usr/bin/env bash
# Ruff(style) 门禁: 锁定现状 baseline, 禁止新增 violations (允许减少).
#
# 说明:
# - 目标是把 D/I/PLC/G 作为“增量门禁”，避免一次性清理全仓库 600+ 条历史问题。
# - baseline 不含行号/列号，避免重排代码导致误报。
#
# 参考：
# - docs/Obsidian/standards/core/gate/ruff-style-baseline.md

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASELINE_FILE="${ROOT_DIR}/scripts/ci/baselines/ruff_style.txt"

UPDATE_BASELINE="false"

if [[ "${1:-}" == "--update-baseline" ]]; then
  UPDATE_BASELINE="true"
  shift
fi

RUFF_CMD=()

if command -v ruff >/dev/null 2>&1; then
  RUFF_CMD=("ruff")
elif [[ -x "${ROOT_DIR}/.venv/bin/ruff" ]]; then
  RUFF_CMD=("${ROOT_DIR}/.venv/bin/ruff")
elif [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/ruff" ]]; then
  RUFF_CMD=("${VIRTUAL_ENV}/bin/ruff")
elif command -v uv >/dev/null 2>&1; then
  RUFF_CMD=("uv" "run" "ruff")
else
  echo "未检测到 ruff/uv, 请先执行 make install/uv sync 安装依赖." >&2
  exit 1
fi

ruff_json_file="$(mktemp)"
current_file="$(mktemp)"
baseline_sorted_file="$(mktemp)"

trap 'rm -f "${ruff_json_file}" "${current_file}" "${baseline_sorted_file}"' EXIT

cd "${ROOT_DIR}"

set +e
"${RUFF_CMD[@]}" check . --select "D,I,PLC,G" --output-format json >"${ruff_json_file}"
ruff_status=$?
set -e

if [[ "${ruff_status}" -eq 2 ]]; then
  echo "Ruff 运行失败(exit 2), 请先修复运行环境或配置错误." >&2
  exit 1
fi

python3 - <<'PY' "${ROOT_DIR}" "${ruff_json_file}" "${current_file}"
import json
import re
import sys
from pathlib import Path

root_dir = Path(sys.argv[1]).resolve()
json_path = Path(sys.argv[2]).resolve()
out_path = Path(sys.argv[3]).resolve()

def normalize_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()

with json_path.open("r", encoding="utf-8") as f:
    payload = json.load(f)

lines: list[str] = []
for diag in payload or []:
    filename = diag.get("filename") or ""
    code = diag.get("code") or ""
    message = normalize_whitespace(diag.get("message") or "")
    try:
        rel_path = str(Path(filename).resolve().relative_to(root_dir))
    except Exception:
        rel_path = str(filename)
    lines.append(f"{rel_path}\t{code}\t{message}")

lines.sort()
out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
PY

current_count="$(wc -l <"${current_file}" | tr -d '[:space:]')"

if [[ "${UPDATE_BASELINE}" == "true" ]]; then
  mkdir -p "$(dirname "${BASELINE_FILE}")"
  cp "${current_file}" "${BASELINE_FILE}"
  echo "已更新 baseline: ${BASELINE_FILE}"
  echo "当前 ruff(style) violations 数: ${current_count}"
  exit 0
fi

if [[ ! -f "${BASELINE_FILE}" ]]; then
  echo "未找到 baseline 文件: ${BASELINE_FILE}" >&2
  echo "请先运行: ./scripts/ci/ruff-style-guard.sh --update-baseline" >&2
  echo "参考：docs/Obsidian/standards/core/gate/ruff-style-baseline.md" >&2
  exit 1
fi

LC_ALL=C sort "${BASELINE_FILE}" >"${baseline_sorted_file}"

new_hits="$(comm -13 "${baseline_sorted_file}" "${current_file}" || true)"
if [[ -n "${new_hits}" ]]; then
  echo "检测到新增的 Ruff(style) violations(禁止新增):" >&2
  echo "${new_hits}" >&2
  echo "如确需更新 baseline, 请运行: ./scripts/ci/ruff-style-guard.sh --update-baseline" >&2
  echo "参考：docs/Obsidian/standards/core/gate/ruff-style-baseline.md" >&2
  exit 1
fi

echo "检查通过: 当前 ruff(style) violations 数 ${current_count} (允许减少, 禁止新增)."
