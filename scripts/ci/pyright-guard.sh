#!/usr/bin/env bash
# pyright 门禁: 锁定现状 baseline, 禁止新增 diagnostics (允许减少).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASELINE_FILE="${ROOT_DIR}/scripts/ci/baselines/pyright.txt"
PYRIGHT_PROJECT_FILE="${ROOT_DIR}/pyrightconfig.json"

UPDATE_BASELINE="false"

if [[ "${1:-}" == "--update-baseline" ]]; then
  UPDATE_BASELINE="true"
  shift
fi

if [[ ! -f "${PYRIGHT_PROJECT_FILE}" ]]; then
  echo "未找到 pyright 配置文件: ${PYRIGHT_PROJECT_FILE}" >&2
  exit 1
fi

PYRIGHT_CMD=()

if command -v pyright >/dev/null 2>&1; then
  PYRIGHT_CMD=("pyright")
elif [[ -x "${ROOT_DIR}/.venv/bin/pyright" ]]; then
  PYRIGHT_CMD=("${ROOT_DIR}/.venv/bin/pyright")
elif [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/pyright" ]]; then
  PYRIGHT_CMD=("${VIRTUAL_ENV}/bin/pyright")
elif command -v uv >/dev/null 2>&1; then
  PYRIGHT_CMD=("uv" "run" "pyright")
else
  echo "未检测到 pyright/uv, 请先执行 make install/uv sync 安装依赖." >&2
  exit 1
fi

pyright_json_file="$(mktemp)"
current_file="$(mktemp)"
baseline_sorted_file="$(mktemp)"

trap 'rm -f "${pyright_json_file}" "${current_file}" "${baseline_sorted_file}"' EXIT

cd "${ROOT_DIR}"

set +e
"${PYRIGHT_CMD[@]}" --project "${PYRIGHT_PROJECT_FILE}" --outputjson >"${pyright_json_file}"
pyright_status=$?
set -e

if [[ "${pyright_status}" -eq 2 ]]; then
  echo "Pyright 运行失败(exit 2), 请先修复运行环境或配置错误." >&2
  exit 1
fi

python3 - <<'PY' "${ROOT_DIR}" "${pyright_json_file}" "${current_file}"
import json
import re
import sys
from pathlib import Path

root_dir = Path(sys.argv[1]).resolve()
json_path = Path(sys.argv[2]).resolve()
out_path = Path(sys.argv[3]).resolve()

def normalize_whitespace(text: str) -> str:
    # Replace any whitespace (including non-breaking spaces) with single spaces.
    text = text.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()

with json_path.open("r", encoding="utf-8") as f:
    payload = json.load(f)

diagnostics = payload.get("generalDiagnostics") or []
lines: list[str] = []
for diag in diagnostics:
    file_path = diag.get("file") or ""
    try:
        rel_path = str(Path(file_path).resolve().relative_to(root_dir))
    except Exception:
        rel_path = str(file_path)

    severity = diag.get("severity") or ""
    rule = diag.get("rule") or ""
    message = normalize_whitespace(diag.get("message") or "")
    lines.append(f"{rel_path}\t{severity}\t{rule}\t{message}")

lines.sort()
out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
PY

current_count="$(wc -l <"${current_file}" | tr -d '[:space:]')"

if [[ "${UPDATE_BASELINE}" == "true" ]]; then
  mkdir -p "$(dirname "${BASELINE_FILE}")"
  cp "${current_file}" "${BASELINE_FILE}"
  echo "已更新 baseline: ${BASELINE_FILE}"
  echo "当前 diagnostics 数: ${current_count}"
  exit 0
fi

if [[ ! -f "${BASELINE_FILE}" ]]; then
  echo "未找到 baseline 文件: ${BASELINE_FILE}" >&2
  echo "请先运行: ./scripts/ci/pyright-guard.sh --update-baseline" >&2
  exit 1
fi

LC_ALL=C sort "${BASELINE_FILE}" >"${baseline_sorted_file}"

new_hits="$(comm -13 "${baseline_sorted_file}" "${current_file}" || true)"
if [[ -n "${new_hits}" ]]; then
  echo "检测到新增的 Pyright diagnostics(禁止新增):" >&2
  echo "${new_hits}" >&2
  echo "如确需更新 baseline, 请运行: ./scripts/ci/pyright-guard.sh --update-baseline" >&2
  exit 1
fi

echo "检查通过: 当前 diagnostics 数 ${current_count} (允许减少, 禁止新增)."
